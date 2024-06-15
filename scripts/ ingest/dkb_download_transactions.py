"""Download transactions from DKB and store in csv file."""

import os
from pprint import pprint
from typing import List
import csv
from babel.numbers import format_number
from dkb_robo import DKBRobo
import datetime
import pandas as pd
from beancount import loader
import json


def download_transactions(
    dkb_session: DKBRobo,
    account_lastfour: str,
    date_from: str,
    date_to: str,
    allow_prebooked: bool = False,
) -> List:
    link_transactions = None

    for account in dkb_session.account_dic.values():
        if account_lastfour in account["account"].replace(" ", ""):
            link_transactions = account["transactions"]
            break

    assert (
        link_transactions is not None
    ), f"Account with last four digits {account_lastfour} not found."
    pprint(link_transactions)

    transactions = dkb_session.get_transactions(
        link_transactions, "account", date_from, date_to, "booked"
    )
    for txn in transactions:
        txn["status"] = "booked"
    if allow_prebooked:
        reserved_txns = dkb_session.get_transactions(
            link_transactions, "account", date_from, date_to, "reserved"
        )
        for txn in reserved_txns:
            txn["status"] = "reserved"
        transactions.extend(reserved_txns)

    balance = format_number(account["amount"], locale="de_DE") + " EUR"

    return transactions, balance


def save_as_csv(
    transactions: List,
    filename: str,
    iban: str,
    account_type: str,
    start_date: str,
    end_date: str,
    balance: str,
):
    with open(filename, "w", newline="", encoding="ISO8859-2") as csvfile:
        writer = csv.writer(
            csvfile, delimiter=";", quotechar='"', quoting=csv.QUOTE_ALL
        )

        # Write header
        writer.writerows(
            [
                ["Kontonummer:", f"{iban} / {account_type}"],
                [],
                ["Von:", start_date],
                ["Bis:", end_date],
                [f"Kontostand vom {end_date}:", balance],
                [],
            ]
        )

        # Write column names
        writer.writerow(
            [
                "Buchungstag",
                "Wertstellung",
                "Buchungstext",
                "Auftraggeber / Begünstigter",
                "Verwendungszweck",
                "Kontonummer",
                "BLZ",
                "Betrag (EUR)",
                "Gläubiger-ID",
                "Mandatsreferenz",
                "Kundenreferenz",
                "Status",
            ]
        )

        for txn in transactions:
            writer.writerow(
                [
                    txn["bdate"],
                    txn["vdate"],
                    txn["postingtext"],
                    txn["peer"],
                    txn["reasonforpayment"],
                    txn["peeraccount"],
                    txn["peerbic"],
                    txn["amount"],
                    txn["peerid"],
                    txn["mandatereference"],
                    txn["customerreferenz"],
                    txn["status"],
                ]
            )


def get_last_transaction_date(path_to_main_bean_file: str) -> str:
    """Parse the last transaction date from the main bean file and return it in the format DD.MM.YYYY."""

    entries, _, _ = loader.load_file(path_to_main_bean_file)
    dates = [entry.date for entry in entries]
    if len(dates) == 0:
        return "01.01.2000"
    return max(dates).strftime("%d.%m.%Y")


def download_all_csv_files(account_info: List, dkb_session: DKBRobo):
    """Download all transactions for all accounts and save them as csv files."""

    for account in account_info:
        account_iban = account["iban"]
        account_type = account["type"]
        account_lastfour = account_iban[-4:]
        bean_file = account["bean_file"]
        save_path = account["save_path"]

        print(
            f"[INFO] Downloading transactions for {account_type} ({account_lastfour})..."
        )

        start_date = get_last_transaction_date(bean_file)
        print(f"[INFO] Parsed start date: {start_date}")
        end_date = datetime.datetime.now().strftime("%d.%m.%Y")
        print(f"[INFO] End date: {end_date}")

        transactions, balance = download_transactions(
            dkb_session, account_lastfour, start_date, end_date, allow_prebooked=True
        )
        csv_path = f"{save_path}/{''.join(start_date.split('.')[::-1])[2:]}-{''.join(end_date.split('.')[::-1])[2:]}.csv"  # format YYMMDD-YYMMDD.csv
        save_as_csv(
            transactions,
            csv_path,
            account_iban,
            account_type,
            start_date,
            end_date,
            balance,
        )


def main():
    with open(os.environ["DKB_ROBO_CONFIG_PATH"], "r", encoding="UTF-8") as json_file:
        account_info = json.load(json_file)

    with DKBRobo(os.environ["DKB_USER"], os.environ["DKB_PASSWORD"]) as dkb_session:
        print("[INFO] Login successful.")
        print(pd.DataFrame(dkb_session.account_dic).T)
        print("---------------")

        download_all_csv_files(account_info, dkb_session)


if __name__ == "__main__":
    main()
