# transactions/fund_transfer.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Fund Transfer Transaction.

"""
from typing import Any
from python_accounting.models import Transaction
from python_accounting.mixins.trading import TradingMixin
from python_accounting.exceptions import (
    FundAccountingDisabledError,
    MissingFundError,
    SameFundTransferError,
)


class FundTransfer(TradingMixin, Transaction):  # pylint: disable=too-many-ancestors
    """Class for the Fund Transfer Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.FUND_TRANSFER,
    }

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Account,
        )

        self.line_item_types: list = [
            Account.AccountType.BANK,
            Account.AccountType.CURRENT_ASSET,
            Account.AccountType.NON_CURRENT_ASSET,
            Account.AccountType.RECEIVABLE,
            Account.AccountType.PAYABLE,
            Account.AccountType.CURRENT_LIABILITY,
            Account.AccountType.NON_CURRENT_LIABILITY,
            Account.AccountType.EQUITY,
            Account.AccountType.RECONCILIATION,
            Account.AccountType.CONTROL,
            Account.AccountType.INVENTORY,
            Account.AccountType.CONTRA_ASSET,
            Account.AccountType.OPERATING_REVENUE,
            Account.AccountType.OPERATING_EXPENSE,
            Account.AccountType.NON_OPERATING_REVENUE,
            Account.AccountType.DIRECT_EXPENSE,
            Account.AccountType.OVERHEAD_EXPENSE,
            Account.AccountType.OTHER_EXPENSE,
        ]
        self.main_account_types: list = list(self.line_item_types)
        self.account_type_map: dict = {}

        self.credited = False
        self.transaction_type = Transaction.TransactionType.FUND_TRANSFER
        self.no_tax = True
        super().__init__(**kw)

    def validate(self, session) -> None:
        """
        Validates the Fund Transfer properties.

        Args:
            session (Session): The accounting session to which the Transaction belongs.

        Raises:
            FundAccountingDisabledError: If fund accounting is not enabled.
            MissingFundError: If source fund is not set.
            SameFundTransferError: If source and destination funds are the same.

        Returns:
            None
        """
        if not session.entity.fund_accounting:
            raise FundAccountingDisabledError

        if self.fund_id is None:
            raise MissingFundError

        for line_item in self.line_items:
            if line_item.fund_id is not None and line_item.fund_id == self.fund_id:
                raise SameFundTransferError

        # Skip TradingMixin.validate account type check, go directly to Transaction.validate
        Transaction.validate(self, session)
