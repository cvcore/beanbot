import csv
import re
from datetime import timedelta
from typing import List

from beancount.core import data, flags
from beancount.core.amount import Amount
from beancount.core.number import D
from beancount.ingest import importer
import dateutil
import parse


def string_cleaning(in_string: str) -> str:
    """Remove extra spaces from a string."""
    return re.sub(" +", " ", in_string)


class Importer(importer.ImporterProtocol):
    def __init__(self, account, lastfour):
        self._account = account
        self._lastfour = lastfour

    def identify(self, f):
        # Match based on filename structure, assuming last four digits are part of the path
        return re.match(rf"^.*dkb/transactions/{self._lastfour}/.*\.csv$", f.name)

    def extract(self, f, existing_entries=None):
        entries = []

        with open(f.name, encoding="UTF-8") as csvfile:
            # Read the new 4-line header
            csv_header = [next(csvfile).strip().replace('"', "") for _ in range(4)]

            # Line 1: Account Type and IBAN
            account_type, account_iban = csv_header[0].split(";")
            # account_type is now available if needed

            assert (
                self._lastfour == account_iban[-4:]
            ), f"Last four digits of IBAN should be {self._lastfour}, got {account_iban[-4:]}"

            # Line 2: Date Range (Optional - not strictly needed for balance/transactions)
            # date_range_str = csv_header[1].split(';')[1]
            # date_begin_str, date_end_str = date_range_str.split(' - ')
            # date_begin = dateutil.parser.parse(date_begin_str, dayfirst=True).date()
            # date_end_report = dateutil.parser.parse(date_end_str, dayfirst=True).date() # End date of the report period

            # Line 3: Balance Date and Amount
            assert csv_header[2].startswith(
                "Kontostand vom"
            ), f"Got invalid balance line: {csv_header[2]}"
            bal_info_str, bal_val_str = csv_header[2].split(";")
            balance_date = parse.search("Kontostand vom {:%d.%m.%Y}", bal_info_str)[0]
            assert (
                balance_date is not None
            ), f"Failed to parse balance date from: {bal_info_str}"
            # Parse balance value and currency
            bal_val, bal_currency = (
                bal_val_str.replace(".", "")
                .replace(",", ".")
                .replace("\xa0", " ")
                .rsplit(
                    " ", 1
                )  # The string may contain non-breaking spaces, remove them
            )
            assert (
                bal_currency == "€" or bal_currency == "EUR"
            ), f"Balance currency should be EUR/€, got {bal_currency}"
            bal_currency = "EUR"  # Standardize to EUR

            balance_amount = Amount(D(bal_val), bal_currency)
            balance = data.Balance(
                meta=data.new_metadata(f.name, 3),  # Line number in header
                date=balance_date
                + timedelta(days=1),  # Beancount balance is start of day after
                account=self._account,
                amount=balance_amount,
                tolerance=None,
                diff_amount=None,
            )
            # Balance directive will be added at the end

            for index, row in enumerate(csv.DictReader(csvfile, delimiter=";")):
                # Check for empty rows often present at the end of DKB CSVs
                if not any(row.values()):
                    continue

                date_booking = dateutil.parser.parse(
                    row["Buchungsdatum"], dayfirst=True
                ).date()
                # ... existing transaction parsing code ...
                payee = string_cleaning(row["Zahlungsempfänger*in"].strip())
                issuer = string_cleaning(row["Zahlungspflichtige*r"].strip())
                if "ISSUER" in issuer:
                    issuer = ""
                purpose = string_cleaning(row["Verwendungszweck"])
                # payee_account = row["Kontonummer"]
                # payee_blz = row["BLZ"]
                trans_amount = row["Betrag (€)"]
                sepa_creditor_id = row["Gläubiger-ID"]
                sepa_mandate_ref = row["Mandatsreferenz"]
                customer_reference = string_cleaning(row["Kundenreferenz"].strip())

                trans_meta = data.new_metadata(
                    f.name, index + 6
                )  # Adjust line number accounting for header
                # Note: For metadata keys must begin with a lowercase character
                if sepa_creditor_id != "":
                    trans_meta["sepa_creator_id"] = sepa_creditor_id
                if sepa_mandate_ref != "":
                    trans_meta["sepa_mandate_reference"] = sepa_mandate_ref

                narration_str = (
                    f"Verwendungszweck: {purpose} Kundenreferenz: {customer_reference}"
                )
                if issuer != "":
                    narration_str += f" Zahlungspflichtiger: {issuer}"
                txn = data.Transaction(
                    meta=trans_meta,
                    date=date_booking,
                    flag=flags.FLAG_WARNING,
                    payee=payee,
                    narration=narration_str,
                    tags=set(),
                    links=set(),
                    postings=[],
                )  # type: ignore
                posting = self._parse_posting(purpose, trans_amount)
                txn.postings.extend(posting)

                entries.append(txn)

        # Add the balance directive at the end of all transactions
        entries.append(balance)

        return entries

    def file_account(self, _):
        return self._account

    def file_name(self, _):
        return "DKB_Transactions"

    def dec_de2intl(self, decimal: str) -> str:
        # if decimal.find(",") == -1:
        #     return decimal
        return decimal.replace(".", "").replace(",", ".")

    def _parse_posting(
        self, trans_purpose: str, trans_amount: str
    ) -> List[data.Posting]:
        postings = list()
        posting_amount = Amount(D(self.dec_de2intl(trans_amount)), "EUR")

        fmt_foreign_trans = "Ursprungsbetrag in Fremdwährung {foreign_units} {foreign_currency:3l} 1 Euro={foreign_price} {:3l}"
        result_foreign_trans = parse.search(fmt_foreign_trans, trans_purpose)

        if result_foreign_trans is not None:
            foreign_currency = result_foreign_trans["foreign_currency"]
            foreign_units = Amount(
                D(self.dec_de2intl(result_foreign_trans["foreign_units"])),
                foreign_currency,
            )  # Units of foreign currency
            foreign_price = Amount(
                D(self.dec_de2intl(result_foreign_trans["foreign_price"])),
                foreign_currency,
            )  # Price of 1 EUR in foreign currency

            fmt_trans_fee = "Fremdentgelt {fee_units} {fee_currency:3l}"
            result_trans_fee = parse.search(fmt_trans_fee, trans_purpose)

            if result_trans_fee is not None:
                assert result_trans_fee["fee_currency"] == foreign_currency
                trans_fee_foreign = Amount(
                    D(self.dec_de2intl(result_trans_fee["fee_units"])), foreign_currency
                )
                trans_fee = Amount(
                    trans_fee_foreign.number / foreign_price.number, "EUR"
                )
                postings = [
                    data.Posting(
                        account="Expenses:Others",  # TODO: Use configurable fee account
                        units=trans_fee,
                        price=foreign_price,
                        cost=None,
                        flag=None,
                        meta=None,
                    ),
                    data.Posting(
                        account=self._account,
                        units=Amount(
                            posting_amount.number + trans_fee.number, "EUR"
                        ),  # Adjust main posting by fee
                        price=foreign_price,
                        cost=None,
                        flag=None,
                        meta=None,
                    ),
                ]

                assert round(
                    (foreign_units.number + trans_fee_foreign.number)
                    / foreign_price.number,
                    2,
                ) == abs(posting_amount.number), f"Currency conversion doesn't match!\
                    ({foreign_units} + {trans_fee_foreign.number} (fee)) {foreign_currency} / {foreign_price} {foreign_currency}/EUR != {posting_amount.number} EUR"

            else:
                # No transaction fee
                postings = [
                    data.Posting(
                        account=self._account,
                        units=Amount(posting_amount.number, "EUR"),
                        price=foreign_price,
                        cost=None,
                        flag=None,
                        meta=None,
                    )
                ]
                assert round(foreign_units.number / foreign_price.number, 2) == abs(
                    posting_amount.number
                ), f"Currency conversion doesn't match!\
                    {foreign_units} / {foreign_price.number} {foreign_price.currency}/EUR != {posting_amount.number} EUR"

        else:
            # Fallback for non-foreign currency transactions
            postings = [
                data.Posting(
                    account=self._account,
                    units=posting_amount,
                    price=None,
                    cost=None,
                    flag=None,
                    meta=None,
                )
            ]

        return postings
