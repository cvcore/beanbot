import csv
import re
from datetime import datetime, timedelta

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

    def __init__(self, account):
        self._account = account

    def identify(self, f):
        return re.match(f"^.*dkb/transactions/((?!archive).)*/.*\.csv$", f.name)

    def extract(self, f, existing_entries=None):
        entries = []

        with open(f.name, encoding='latin-1') as csvfile:

            csv_header = [next(csvfile) for _ in range(6)]
            account_info = parse.parse('"Kontonummer:";"{account_iban} / Girokonto";', csv_header[0].strip())
            assert account_info is not None
            account_iban = account_info['account_iban']

            date_begin = dateutil.parser.parse(csv_header[2].split(';')[1].replace('"', ''), dayfirst=True).date()
            date_end = dateutil.parser.parse(csv_header[3].split(';')[1].replace('"', ''), dayfirst=True).date()

            bal_val, bal_currency = csv_header[4].split(';')[1].replace('"', '').replace('.', '').replace(',', '.').split(' ')
            assert bal_currency == 'EUR', f"Balance currency should be in EUR, got {bal_currency}"

            balance_amount = Amount(D(bal_val), 'EUR')
            balance = data.Balance(
                meta=data.new_metadata(f.name, 4),
                date=date_end+timedelta(days=1),
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
                trans_amount = row['Betrag (EUR)'].replace('.', '').replace(',', '.')
                sepa_creditor_id = row['Gläubiger-ID']
                sepa_mandate_ref = row['Mandatsreferenz']
                customer_reference = string_cleaning(row['Kundenreferenz'].strip())

                trans_meta = data.new_metadata(f.name, index)
                if sepa_creditor_id != '':
                    trans_meta['SEPA_CREATOR_ID'] = sepa_creditor_id
                if sepa_mandate_ref != '':
                    trans_meta['SEPA_MANDATE_REFERENCE'] = sepa_mandate_ref

                txn = data.Transaction(
                    meta=trans_meta,
                    date=date_booking,
                    flag=flags.FLAG_OKAY,
                    payee=payee,
                    narration=f"Verwendungszweck: {purpose} Kundenreferenz: {customer_reference}",
                    tags=set(),
                    links=set(),
                    postings=[],
                )

                posting = self._parse_posting(booking_type, purpose, trans_amount)
                txn.postings.append(posting)

                entries.append(txn)

        return entries

    def file_account(self, _):
        return self._account

    def file_name(self, _):
        return "DKB_Transactions"

    def _parse_posting(self, booking_type: str, trans_purpose: str, trans_amount: str) -> data.Posting:
        posting = None
        settle_amount = Amount(D(trans_amount), 'EUR')

        if booking_type == 'Kartenzahlung':
            result = parse.parse('{date:ti}{:s}Debitk.{:d} Original {orig_units} {orig_currency} 1 Euro={orig_price} {} VISA Debit', trans_purpose)
            if result is not None:
                orig_units = Amount(D(result['orig_units'].replace('.', '').replace(',', '.')), result['orig_currency']) # Units of foreign currency
                orig_price = Amount(D(result['orig_price'].replace('.', '').replace(',', '.')), result['orig_currency']) # Price of 1 EUR in foreign currency
                assert round(orig_units.number / orig_price.number, 2) == abs(settle_amount.number), f"Currency conversion doesn't match! {orig_price} / {settle_amount.currency} * {abs(settle_amount.number)} {settle_amount.currency} != {orig_units}"
                posting = data.Posting(account=self._account, units=settle_amount, price=orig_price, cost=None, flag=None, meta=None)

        if posting is None:
            posting = data.Posting(account=self._account, units=settle_amount, price=None, cost=None, flag=None, meta=None)

        return posting
