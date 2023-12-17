import csv
from locale import currency
import re
from datetime import datetime, timedelta
from typing import List

from beancount.core import account, amount, data, flags
from beancount.core.amount import Amount
from beancount.core.number import D
from beancount.core.position import Cost
from beancount.ingest import importer
import dateutil
import parse


def string_cleaning(in_string: str) -> str:
    return re.sub(' +', ' ', in_string)


class Importer(importer.ImporterProtocol):

    def __init__(self, account, lastfour):
        self._account = account
        self._lastfour = lastfour

    def identify(self, f):
        return re.match(f"^.*dkb/transactions/{self._lastfour}/.*\.csv$", f.name)

    def extract(self, f, existing_entries=None):
        entries = []

        with open(f.name, encoding='latin-1') as csvfile:

            csv_header = [next(csvfile) for _ in range(6)]
            account_info = parse.parse('"Kontonummer:";"{iban} / {type}"{}', csv_header[0] + ';')
            assert account_info is not None
            account_iban = account_info['iban']
            # account_type = account_info['type']

            assert self._lastfour == account_iban[-4:], f"Last four digits of IBAN should be {self._lastfour}, got {account_iban[-4:]}"

            date_begin = dateutil.parser.parse(csv_header[2].split(';')[1].replace('"', ''), dayfirst=True).date()
            date_end = dateutil.parser.parse(csv_header[3].split(';')[1].replace('"', ''), dayfirst=True).date()

            bal_val, bal_currency = csv_header[4].strip().split(';')[1].replace('"', '').replace('.', '').replace(',', '.').split(' ')
            assert bal_currency == 'EUR', f"Balance currency should be in EUR, got {bal_currency}"

            balance_amount = Amount(D(bal_val), 'EUR')
            balance = data.Balance(
                meta=data.new_metadata(f.name, 4),
                date=date_end+timedelta(days=1), # Beancount assumes begin-of-day balance value
                account=self._account,
                amount=balance_amount,
                tolerance=None,
                diff_amount=None
            )
            entries.append(balance)

            for index, row in enumerate(csv.DictReader(csvfile, delimiter=';')):

                date_booking = dateutil.parser.parse(row['Buchungstag'], dayfirst=True).date()
                date_value = dateutil.parser.parse(row['Wertstellung'], dayfirst=True).date()
                booking_type = row['Buchungstext']
                payee = string_cleaning(row['Auftraggeber / Begünstigter'].strip())
                purpose = string_cleaning(row['Verwendungszweck'])
                payee_account = row['Kontonummer']
                payee_blz = row['BLZ']
                trans_amount = row['Betrag (EUR)']
                sepa_creditor_id = row['Gläubiger-ID']
                sepa_mandate_ref = row['Mandatsreferenz']
                customer_reference = string_cleaning(row['Kundenreferenz'].strip())

                trans_meta = data.new_metadata(f.name, index)
                # Note: For metadata keys must begin with a lowercase character
                if sepa_creditor_id != '':
                    trans_meta['sepa_creator_id'] = sepa_creditor_id
                if sepa_mandate_ref != '':
                    trans_meta['sepa_mandate_reference'] = sepa_mandate_ref

                txn = data.Transaction(
                    meta=trans_meta,
                    date=date_booking,
                    flag=flags.FLAG_OKAY,
                    payee=payee,
                    narration=f"Buchungstext: {booking_type} Verwendungszweck: {purpose} Kundenreferenz: {customer_reference}",
                    tags=set(),
                    links=set(),
                    postings=[],
                )
                posting = self._parse_posting(booking_type, purpose, trans_amount)
                txn.postings.extend(posting)

                entries.append(txn)

        return entries

    def file_account(self, _):
        return self._account

    def file_name(self, _):
        return "DKB_Transactions"

    def dec_de2intl(self, decimal: str) -> str:
        if decimal.find(',') == -1:
            return decimal
        return decimal.replace('.', '').replace(',', '.')

    def _parse_posting(self, booking_type: str, trans_purpose: str, trans_amount: str) -> List[data.Posting]:
        postings = list()
        posting_amount = Amount(D(self.dec_de2intl(trans_amount)), 'EUR')

        fmt_foreign_trans = "Original {foreign_units} {foreign_currency:3l} 1 Euro={foreign_price} {:3l}"
        result_foreign_trans = parse.search(fmt_foreign_trans, trans_purpose)

        if result_foreign_trans is not None:
            foreign_currency = result_foreign_trans['foreign_currency']
            foreign_units = Amount(D(self.dec_de2intl(result_foreign_trans['foreign_units'])), foreign_currency) # Units of foreign currency
            foreign_price = Amount(D(self.dec_de2intl(result_foreign_trans['foreign_price'])), foreign_currency) # Price of 1 EUR in foreign currency

            fmt_trans_fee = "Fremdentgelt {fee_units} {fee_currency:3l}"
            result_trans_fee = parse.search(fmt_trans_fee, trans_purpose)

            if result_trans_fee is not None:
                assert result_trans_fee['fee_currency'] == foreign_currency
                trans_fee_foreign = Amount(D(self.dec_de2intl(result_trans_fee['fee_units'])), foreign_currency)
                trans_fee = Amount(trans_fee_foreign.number / foreign_price.number, 'EUR')
                postings = [
                    data.Posting(account="Expenses:Others", units=trans_fee, price=foreign_price, cost=None, flag=None, meta=None),
                    data.Posting(account=self._account, units=Amount(posting_amount.number, 'EUR'), price=foreign_price, cost=None, flag=None, meta=None)
                ]
                # TODO: use fee account in config
                assert round((foreign_units.number + trans_fee_foreign.number) / foreign_price.number, 2) == abs(posting_amount.number), f"Currency conversion doesn't match!\
                    ({foreign_units} + {trans_fee_foreign.number} (fee)) {foreign_currency} / {foreign_price} {foreign_currency}/EUR != {posting_amount.number} EUR"

            else:
                # No transaction fee
                postings = [
                    data.Posting(account=self._account, units=Amount(posting_amount.number, 'EUR'), price=foreign_price, cost=None, flag=None, meta=None)
                ]
                assert round(foreign_units.number / foreign_price.number, 2) == abs(posting_amount.number), f"Currency conversion doesn't match!\
                    {foreign_units} / {foreign_price.number} {foreign_price.currency}/EUR != {posting_amount.number} EUR"

        else:
            # Fallback
            postings = [
                data.Posting(account=self._account, units=posting_amount, price=None, cost=None, flag=None, meta=None)
            ]

        return postings
