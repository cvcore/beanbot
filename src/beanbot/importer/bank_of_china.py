import csv
import os
import re

import titlecase
from beancount.core import account, data, flags
from beancount.core.amount import Amount
from beancount.core.number import D
from beancount.core.position import Cost
from beancount.ingest import importer
from dateutil.parser import parse


def get_currency(currency):
    """ helper function to convert currency name in Chinese into standard abbreviations
    """
    conv_dict = {'人民币元': 'CNY',
                 '美元': 'USD',
                 '欧元': 'EUR',
                 '日元': 'JPY',
                 '英镑': 'GBP'}

    assert currency in conv_dict, "Got unknown currency: f{currency}. Please add it into conv_dict!"
    return conv_dict[currency]

class Importer(importer.ImporterProtocol):

    def __init__(self, account, currency='CNY'):
        self.account = account
        self.currency = currency

    def identify(self, f):
        return re.match(f"^.*boc/transactions/((?!archive).)*/.*\.csv$", f.name)

    def extract(self, f, existing_entries=None):
        entries = []

        with open(f.name, encoding='UTF-16-LE') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile, delimiter='\t')):
                trans_date = parse(row['\ufeff交易日期'], yearfirst=True).date()
                trans_payee = row['对方账户名称']
                trans_narration = f"{row['业务摘要']} {row['附言']}"
                trans_currency = get_currency(row['币种'])
                if trans_currency != self.currency:
                    continue
                trans_account = f"{self.account}"
                income_amount = row['收入金额'].replace(',', '')
                outgoing_amount = row['支出金额'].replace(',', '')
                if income_amount:
                    trans_amount = Amount(D(income_amount), trans_currency)
                else:
                    trans_amount = Amount(-D(outgoing_amount), trans_currency)


                meta = data.new_metadata(f.name, index)

                txn = data.Transaction(
                    meta=meta,
                    date=trans_date,
                    flag=flags.FLAG_OKAY,
                    payee=trans_payee,
                    narration=trans_narration,
                    tags=set(),
                    links=set(),
                    postings=[],
                )

                txn.postings.append(
                    data.Posting(trans_account, trans_amount, None, None, None, None)
                )

                entries.append(txn)

        return entries
