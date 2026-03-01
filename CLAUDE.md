# Python Accounting

Double-entry accounting library built on SQLAlchemy.

## Commands

```bash
# Install
poetry install

# Run tests
poetry run pytest

# Run linter
poetry run pylint ./python_accounting

# Run both (via tox)
tox
```

## Architecture

- `python_accounting/models/` — Core models (Account, Transaction, Ledger, LineItem, Entity, etc.)
- `python_accounting/transactions/` — 10 transaction types (CashSale, ClientInvoice, SupplierBill, JournalEntry, etc.)
- `python_accounting/reports/` — Financial statements (IncomeStatement, BalanceSheet, CashflowStatement, TrialBalance, AgingSchedule)
- `python_accounting/mixins/` — Reusable behaviors (IsolatingMixin, ClearingMixin, AssigningMixin, BuyingMixin, SellingMixin)
- `python_accounting/database/` — Session management, event listeners, hashing
- `python_accounting/exceptions/` — Custom exception classes
- `config.toml` — Account types, transaction types, report section definitions

## Key Conventions

- **Transaction polymorphism**: `Transaction` is the base; each of the 10 types is a subclass using SQLAlchemy single-table inheritance.
- **Ledger posting**: `transaction.post(session)` creates paired debit/credit `Ledger` rows. Never create Ledger rows directly.
- **Entity isolation**: All models use `IsolatingMixin` to scope data to an `entity_id`. Queries are auto-filtered.
- **Soft deletes**: Models inherit `Recyclable`; deletion sets `deleted_at` rather than removing rows.
- **Validation hooks**: `validate()` runs on `session.add()`/`session.commit()`; `validate_delete()` on delete.
- **Hash integrity**: Ledger entries are SHA-256 hash-chained (configured in `config.toml`).
- **Test DB**: Tests use in-memory SQLite (`sqlite://`). Fixtures: `engine`, `session`, `entity`, `currency` in `conftest.py`.

## Detailed Analysis

See `_REPO_ANALYSIS.md` for comprehensive architecture docs including the full double-entry posting flow, account/transaction type tables, clearing/assignment system, and report generation.
