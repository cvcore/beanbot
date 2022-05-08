import csv
import re
from datetime import datetime

from beancount.core import account, amount, data, flags
from beancount.core.number import D
from beancount.core.position import Cost
from beancount.ingest import importer
from dateutil.parser import parse


class Importer(importer.ImporterProtocol):

    def __init__(self, account):
        self._account = account

    def identify(self, f):
        return re.match(f"^.*deutsche_bank/transactions/((?!archive).)*/.*\.csv$", f.name)

    def extract(self, f, existing_entries=None):
        entries = []

        with open(f.name, encoding='latin-1') as csvfile:

            for index, row in enumerate(csv.DictReader(csvfile, delimiter=';')):

                trans_date = parse(row['Datum'], dayfirst=True).date()
                trans_payee = row['Auftraggeber / Empfänger']
                trans_narration = row['Verwendungszweck']
                trans_amount = row['Betrag'].replace(',', '.')
                trans_meta = data.new_metadata(f.name, index)
                # trans_meta['__source__'] = ';'.join(list(row.values()))

                txn = data.Transaction(
                    meta=trans_meta,
                    date=trans_date,
                    flag=flags.FLAG_OKAY,
                    payee=trans_payee,
                    narration=trans_narration,
                    tags=set(),
                    links=set(),
                    postings=[],
                )

                txn.postings.append(
                    data.Posting(self._account, amount.Amount(D(trans_amount),
                        'EUR'), None, None, None, None)
                )

                entries.append(txn)

        return entries

    def file_account(self, _):
        return self._account

    def file_name(self, _):
        return "Deutsche_Bank_Transaktionen"

    def file_date(self, file):
        date_str = re.search('\d{2}\-\d{2}\-\d{4}', str(file)).group(0)
        return datetime.strptime(date_str, '%d-%m-%Y').date()
