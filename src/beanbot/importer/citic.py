import re

import dateparser
import pandas
from beancount.core import data, flags
from beancount.core.amount import Amount
from beancount.core.number import D
from beancount.ingest import importer


def get_currency(currency):
    """helper function to convert currency name in Chinese into standard abbreviations"""
    conv_dict = {
        "人民币": "CNY",
        "美元": "USD",
        "欧元": "EUR",
        "日元": "JPY",
        "英镑": "GBP",
        "瑞士法郎": "CHF",
    }

    assert (
        currency in conv_dict
    ), f"Got unknown currency: {currency}. Please add it into conv_dict!"
    return conv_dict[currency]


class Importer(importer.ImporterProtocol):
    def __init__(self, account, lastfour):
        self.account = account
        self.lastfour = lastfour

    def identify(self, file):
        """
        assert raw transaction records are stored as:
        .../citic/transactions/[last_four]/YYYYMM.xls
        processed raw transactions are stored under:
        .../citic/transactions/archive/[last_four]/YYYYMM.xls
        """
        # return re.match('.*\.xls', os.path.basename(f.name))
        # return re.match(f"^.*citic/transactions/((?!archive).)*/.*\.xls$", file.name)
        return re.match(
            r"^.*citic/transactions/" + self.lastfour + r"/.*\.xls$", file.name
        )

    def extract(self, file, existing_entries=None):
        """
        format example (6393):
        交易日期	入账日期	交易描述	卡末四位	交易币种	结算币种	交易金额	结算金额
        2019年11月15日	20191116	PAYPAL *APPLE.COM/BILL   35314369001  GBR	6393	欧元	人民币	1.09	8.52
        ----
        example (2094)
        交易日期	入账日期	交易描述	卡末四位	交易币种	结算币种	交易金额	结算金额
        2020年08月16日	20200816	利息	2094	人民币	人民币	1.41	1.41
        """
        entries = []
        try:
            dataframe = pandas.read_excel(io=file.name, sheet_name="本期账单明细")
        except ValueError:
            dataframe = pandas.read_excel(
                io=file.name, sheet_name="本期账单明细(人民币)"
            )
        lastfour = file.name.rsplit("/")[-2]
        assert lastfour == self.lastfour

        for index, row_data in dataframe.iterrows():
            # check the table heads as verification
            if index == 0:
                assert (
                    list(row_data)
                    == [
                        "交易日期",
                        "入账日期",
                        "交易描述",
                        "卡末四位",
                        "交易币种",
                        "结算币种",
                        "交易金额",
                        "结算金额",
                    ]
                ), "The data format has changed! Please consider updating ecitic.py importer!"
                continue

            trans_date = dateparser.parse(row_data.iloc[0]).date()
            trans_narration = row_data.iloc[2]
            trans_lastfour = row_data.iloc[3]
            assert (
                trans_lastfour == lastfour
            ), f"Found invalid last four digit {trans_lastfour}, expect {lastfour}. Please double check!"
            trans_currency = get_currency(row_data.iloc[4])
            settle_currency = get_currency(row_data.iloc[5])
            assert (
                settle_currency == "CNY"
            ), f"Invalid settlement currency {settle_currency} for account {self.account} card {lastfour}"
            trans_amount = Amount(
                -D(row_data.iloc[7]), settle_currency
            )  # CITIC uses + for payments and - for income.
            if settle_currency != trans_currency:
                rate = Amount(D(row_data.iloc[6]) / D(row_data.iloc[7]), trans_currency)
            else:
                rate = None

            meta = data.new_metadata(file.name, index)

            txn = data.Transaction(
                meta=meta,
                date=trans_date,
                flag=flags.FLAG_OKAY,
                payee="",
                narration=trans_narration,
                tags=set(),
                links=set(),
                postings=[],
            )

            txn.postings.append(
                data.Posting(self.account, trans_amount, None, rate, None, None)
            )

            entries.append(txn)

        return entries
