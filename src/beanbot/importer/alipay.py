import re
from re import Match
from typing import List
from parse import parse

from beancount.core.data import Directive, Transaction, Amount, Posting, new_metadata
from beancount.core.number import D, MISSING

from .csv_importer import CSVImporter
from datetime import datetime

class Importer(CSVImporter):

    FIELD_TRANSACTION_ID = "alipay_transaction_id"
    FIELD_MERCHANT_ID = "alipay_merchant_id"
    FIELD_TRANSACTION_CREATION_TIME = "alipay_transaction_creation_time"
    FIELD_TRANSACTION_PAYMENT_TIME = "alipay_transaction_payment_time"
    FIELD_TRANSACTION_UPDATE_TIME = "alipay_transaction_update_time"
    FIELD_TRANSACTION_NOTES = "alipay_transaction_notes"
    FIELD_AWAITS_RECONCILE = "alipay_awaits_reconcile"

    def __init__(self, account: str, commission_account: str = "Expenses:Financial:Commissions"):
        super().__init__(
            account,
            encoding="GB2312",
            delimiter=",",
            n_header_lines=4,
            n_footer_lines=7,
            skiptrailingspace=True,
        )
        self._commission_account = commission_account

    def identify(self, file) -> Match[str] | None:
        print(file.name)
        return re.match(f"^.*alipay/transactions/((?!archive).)*/.*\.csv$", file.name)

    def _parse_header(self, header_lines: List) -> List[Directive]:
        """
        支付宝交易记录明细查询
        账号:[foo@bar.com]
        起始日期:[2023-01-01 00:00:00]    终止日期:[2024-01-01 01:01:01]
        ---------------------------------交易记录明细列表------------------------------------
        """
        # Validate header lines
        assert "支付宝交易记录明细查询" in header_lines[0]
        assert "账号:" in header_lines[1]
        assert "起始日期:" in header_lines[2]
        assert "终止日期:" in header_lines[2]
        assert "交易记录明细列表" in header_lines[3]

        self._file_meta["alipay_account"] = header_lines[1].split(":")[1].strip().replace("[", "").replace("]", "")
        txn_dates = parse("起始日期:[{start_date}]{}终止日期:[{end_date}]{}", header_lines[2])
        assert txn_dates['start_date'] and txn_dates['end_date'], "Could not parse transaction dates"
        self._file_meta["alipay_txn_start_date"] = txn_dates['start_date']
        self._file_meta["alipay_txn_end_date"] = txn_dates['end_date']

        return []

    def _parse_footer(self, footer_lines: List) -> List[Directive]:
        """
        ------------------------------------------------------------------------------------
        共13笔记录
        已收入:10笔,1234.56元
        待收入:0笔,0.00元
        已支出:3笔,2346,78元
        待支出:0笔,0.00元
        导出时间:[2024-01-01 01:01:02]    用户:张三
        """
        return []

    def _parse_row_impl(self, row: dict, filename: str, lineno: int) -> List[Directive]:
        """
        Sample row:
        交易号                  ,商家订单号               ,交易创建时间              ,付款时间                ,最近修改时间              ,交易来源地     ,类型              ,交易对方            ,商品名称                ,金额（元）   ,收/支     ,交易状态    ,服务费（元）   ,成功退款（元）  ,备注                  ,资金状态     ,
        2024051522001475751429134868	,MT8WVMFZS8a0        	,2024-05-15 07:01:22 ,2024-05-15 07:01:23 ,2024-05-15 07:01:23 ,其他（包括阿里巴巴和外部商家）,即时到账交易          ,App Store & Apple Music,App Store & Apple Music；05.15购买,15.00   ,支出      ,交易成功    ,0.00     ,0.00     ,                    ,已支出      ,

        Note: the trailing whitespaces are to be removed from the parent class
        """
        txn_id = row["交易号"]
        txn_merchant_id = row["商家订单号"]
        txn_creation_time = datetime.strptime(row["交易创建时间"], "%Y-%m-%d %H:%M:%S")
        txn_source = row["交易来源地"]
        txn_type = row["类型"]
        txn_payee = row["交易对方"]
        txn_narration = row["商品名称"]
        txn_amount = row["金额（元）"]
        txn_direction = row["收/支"]
        txn_status = row["交易状态"]
        txn_commision = row["服务费（元）"]
        txn_refund = row["成功退款（元）"]
        txn_notes = row["备注"]
        txn_fund_status = row["资金状态"]

        # Parse metadata
        txn_meta = {
            self.FIELD_TRANSACTION_ID: txn_id,
            self.FIELD_TRANSACTION_CREATION_TIME: str(txn_creation_time),
            self.FIELD_MERCHANT_ID: txn_merchant_id,
        }
        if txn_notes:
            txn_meta[self.FIELD_TRANSACTION_NOTES] = txn_notes

        # Parse postings
        account_amount = D(txn_amount)
        commission_amount = D(txn_commision)
        refund_amount = D(txn_refund)
        txn_postings = []

        if txn_direction == "支出":
            txn_postings.append(
                Posting(
                    account=self._account,
                    units=Amount(-account_amount - commission_amount, "CNY"),  # alipay only reports the net amount in the amount column, so we need to add the commission to get the gross amount
                    cost=None,
                    price=None,
                    flag=None,
                    meta=None,
                )
            )
            if commission_amount > 0:
                txn_postings.append(
                    Posting(account=self._commission_account, units=Amount(commission_amount, "CNY"), cost=None, price=None, flag=None, meta=None)
                )
            if refund_amount > 0:
                txn_meta[self.FIELD_AWAITS_RECONCILE] = "True"  # we split the refund into a separate transaction, so we can reconcile it later more
                                                                # easily by matching the date and the amount.

        elif txn_direction == "收入":
            assert txn_status == "交易成功", f"Incoming transaction {txn_id} is not successful"
            assert txn_fund_status == "已收入", f"Incoming transaction {txn_id} is not marked as received"
            txn_postings.append(
                Posting(
                    account=self._account,
                    units=Amount(account_amount, "CNY"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta=None,
                )
            )
            if commission_amount > 0:
                txn_postings.append(
                    Posting(account=self._commission_account, units=Amount(commission_amount, "CNY"), cost=None, price=None, flag=None, meta=None)
                )
            if refund_amount > 0:
                raise NotImplementedError("Refunds for incoming transactions are not yet supported")

        elif txn_direction == "不计收支":
            if txn_fund_status == "资金转移":
                txn_postings.append(
                    Posting(
                        account=self._account,
                        units=Amount(-account_amount - commission_amount, "CNY"),
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                )
                if commission_amount > 0:
                    txn_postings.append(
                        Posting(account=self._commission_account, units=Amount(commission_amount, "CNY"), cost=None, price=None, flag=None, meta=None)
                    )
                txn_postings.append(
                    Posting(
                        account="Assets:Transfer",
                        units=Amount(account_amount, "CNY"),
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                )
            elif txn_fund_status == "已收入":
                assert commission_amount == 0, f"Commission for refund transaction {txn_id} is not zero"
                assert account_amount > 0, f"Amount for refund transaction {txn_id} is not positive"
                assert refund_amount == 0, f"Refund amount for transaction {txn_id} is not zero"

                txn_postings.append(
                    Posting(
                        account=self._account,
                        units=Amount(refund_amount, "CNY"),
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                )
                txn_meta[self.FIELD_AWAITS_RECONCILE] = "True"  # we split the refund into a separate transaction, so we can reconcile it later more
            elif txn_fund_status == "":
                return []
            else:
                raise ValueError(f"未知资金状态: {txn_fund_status}")
        else:
            raise ValueError(f"未知收支类型: {txn_direction}")

        txn_postings.append(
            Posting(
                account="Expenses:FIXME",
                units=None,
                cost=None,
                price=None,
                flag=None,
                meta=None,
            )
        )

        # Create transaction
        txn = Transaction(  # type: ignore
            meta=new_metadata(filename, lineno, kvlist=txn_meta),
            date=txn_creation_time.date(),
            flag=self.FLAG,
            payee=txn_payee,
            narration=txn_narration,
            tags=set(),
            links=set(),
            postings=txn_postings,
        )

        return [txn]
