# Python Accounting — Repository Analysis

## Overview

This is a full double-entry accounting system built in Python with SQLAlchemy. It enforces the fundamental accounting equation (**Assets = Liabilities + Equity**) through automatic ledger posting, supports 10 transaction types, generates standard financial reports, and provides multi-entity isolation with hash-based integrity checking.

---

## How Double-Entry Accounting Works in This Codebase

### The Core Principle

Every financial event creates **two equal and opposite ledger entries** — a debit and a credit. This ensures the books always balance. The system enforces this automatically: when a `Transaction` is posted, the `Ledger.post()` method creates paired records so that total debits always equal total credits.

### The Posting Flow

```
Transaction (e.g. CashSale)
  ├── main_account  (BANK)        ← receives DEBIT
  └── LineItem
        └── account (REVENUE)     ← receives CREDIT
```

1. **User creates a Transaction** with a `main_account_id` (the "post account") and one or more `LineItem` objects, each pointing to a different account (the "folio account").
2. **`transaction.post(session)`** is called, which delegates to `Ledger.post()`.
3. **`Ledger.post()` creates ledger entry pairs** — for each line item, two `Ledger` rows are inserted:
   - One debiting the post account
   - One crediting the folio account (or vice-versa, controlled by the `credited` flag)
4. **Tax entries** (if any) generate additional ledger pairs posting to the tax account.
5. **Hashing** — every ledger row is SHA-256 hashed (chained to the previous hash) to detect tampering.

### credited Flag

The `Transaction.credited` flag controls which side each account lands on:

| `credited` | Post Account | Folio Account |
|------------|-------------|---------------|
| `False`    | DEBIT       | CREDIT        |
| `True`     | CREDIT      | DEBIT         |

### Compound Journal Entries

A `JournalEntry` with `compound=True` allows multiple debits and multiple credits in a single transaction. The `_allocate_amount()` method recursively distributes amounts across line items, and validation ensures total debits equal total credits before posting.

---

## Key Data Models

### Entity Hierarchy

```
Entity (reporting company)
  ├── Currency
  ├── ReportingPeriod (OPEN → ADJUSTING → CLOSED)
  ├── Account (16 types, serial codes)
  │     ├── Category (optional grouping)
  │     └── Balance (opening balances from prior periods)
  ├── Tax
  └── Transaction (10 types, polymorphic)
        ├── LineItem (the "other side" of entries)
        ├── Ledger (the actual debit/credit postings)
        └── Assignment (links payments to invoices)
```

### Account Types (16)

| Type | Code Range | Nature |
|------|-----------|--------|
| NON_CURRENT_ASSET | 0–999 | Debit |
| CONTRA_ASSET | 1000–1999 | Credit |
| INVENTORY | 2000–2999 | Debit |
| BANK | 3000–3999 | Debit |
| CURRENT_ASSET | 4000–4999 | Debit |
| RECEIVABLE | 50000–99999 | Debit |
| NON_CURRENT_LIABILITY | 5000–5999 | Credit |
| CONTROL | 6000–6999 | Credit |
| CURRENT_LIABILITY | 7000–7999 | Credit |
| PAYABLE | 20000–49999 | Credit |
| RECONCILIATION | 8000–8999 | Credit |
| EQUITY | 9000–9999 | Credit |
| OPERATING_REVENUE | 11000–11999 | Credit |
| OPERATING_EXPENSE | 12000–12999 | Debit |
| NON_OPERATING_REVENUE | 13000–13999 | Credit |
| DIRECT_EXPENSE | 14000–14999 | Debit |
| OVERHEAD_EXPENSE | 15000–15999 | Debit |
| OTHER_EXPENSE | 16000–16999 | Debit |

### Transaction Types (10)

| Type | Prefix | Main Account | Line Item Accounts | credited |
|------|--------|-------------|-------------------|----------|
| **CASH_SALE** | CS | BANK | OPERATING_REVENUE | False |
| **CLIENT_INVOICE** | IN | RECEIVABLE | OPERATING_REVENUE | False |
| **CREDIT_NOTE** | CN | RECEIVABLE | OPERATING_REVENUE | True |
| **CLIENT_RECEIPT** | RC | RECEIVABLE | BANK | True |
| **CASH_PURCHASE** | CP | BANK | Purchasables* | True |
| **SUPPLIER_BILL** | BL | PAYABLE | Purchasables* | True |
| **DEBIT_NOTE** | DN | PAYABLE | Purchasables* | False |
| **SUPPLIER_PAYMENT** | PY | PAYABLE | BANK | False |
| **CONTRA_ENTRY** | CE | BANK | BANK | False |
| **JOURNAL_ENTRY** | JN | Any | Any | Either |

\* Purchasables: NON_CURRENT_ASSET, CONTRA_ASSET, INVENTORY, CURRENT_ASSET, OPERATING_EXPENSE, DIRECT_EXPENSE, OVERHEAD_EXPENSE, OTHER_EXPENSE, NON_OPERATING_REVENUE

---

## Transaction Clearing & Assignment

The system tracks which payments clear which invoices through the `Assignment` model.

### Clearable Transactions (can be paid off)
- CLIENT_INVOICE
- SUPPLIER_BILL
- JOURNAL_ENTRY

### Assignable Transactions (used to pay off others)
- CLIENT_RECEIPT → clears CLIENT_INVOICE
- SUPPLIER_PAYMENT → clears SUPPLIER_BILL
- CREDIT_NOTE → clears CLIENT_INVOICE
- DEBIT_NOTE → clears SUPPLIER_BILL
- JOURNAL_ENTRY → clears any clearable

### Example: Paying an Invoice

```python
# 1. Create invoice (IN-0001)
invoice = ClientInvoice(main_account_id=receivable.id, ...)
invoice.line_items.append(LineItem(account_id=revenue.id, amount=1000))
invoice.post(session)

# 2. Receive payment (RC-0001)
receipt = ClientReceipt(main_account_id=receivable.id, ...)
receipt.line_items.append(LineItem(account_id=bank.id, amount=1000))
receipt.post(session)

# 3. Assign receipt to invoice
assignment = Assignment(
    assignment_date=date.today(),
    transaction_id=receipt.id,      # the assignable
    assigned_id=invoice.id,         # the clearable
    amount=1000
)
```

Validation prevents:
- **Self-clearance** — a transaction clearing itself
- **Over-clearance** — clearing more than the outstanding amount
- **Insufficient balance** — assigning more than the payment amount

---

## Ledger Integrity & Hashing

Every `Ledger` row is hashed using SHA-256 (configurable). The hash chain works like a blockchain:

```
hash = SHA256(date + entry_type + amount + previous_hash + entity + transaction + currency + accounts + line_item + tax)
```

- `Ledger.is_secure()` re-computes and verifies all hashes
- Detects any retroactive tampering with posted entries

---

## Mixins Architecture

| Mixin | Purpose | Used By |
|-------|---------|---------|
| **IsolatingMixin** | Adds `entity_id` FK; scopes queries to one entity | Account, Transaction, Ledger, LineItem, etc. |
| **ClearingMixin** | `cleared()`, `clearances()`, `unclear()` | ClientInvoice, SupplierBill, JournalEntry |
| **AssigningMixin** | `balance()`, `assignments()`, `unassign()` | ClientReceipt, SupplierPayment, CreditNote, DebitNote, JournalEntry |
| **TradingMixin** | Validates main/line-item account types | (base for Buying/Selling) |
| **BuyingMixin** | Restricts to purchasable accounts | SupplierBill, CashPurchase, DebitNote |
| **SellingMixin** | Restricts to revenue accounts | ClientInvoice, CashSale, CreditNote |

---

## Tax Handling

Two modes per line item:

- **Tax-Exclusive** (`tax_inclusive=False`): Tax is added on top of the line item amount. Ledger posts the tax amount separately to the tax account.
- **Tax-Inclusive** (`tax_inclusive=True`): Tax is extracted from the line item amount using `amount - (amount / (1 + rate))`. The net amount posts to the line item account; the tax portion posts to the tax account.

---

## Financial Reports

All reports inherit from `FinancialStatement` and query ledger/balance data by account type.

### Income Statement (Profit & Loss)
- **Sections**: Operating Revenues, Operating Expenses, Non-Operating Revenues, Non-Operating Expenses
- **Results**: Gross Profit, Total Revenue, Total Expenses, Net Profit
- Movement-based (period start → end)

### Balance Sheet
- **Sections**: Assets, Liabilities, Equity
- **Results**: Net Assets, Total Equity
- Point-in-time snapshot; incorporates net profit from Income Statement

### Cash Flow Statement
- **Sections**: Operating, Investment, Financing cash flows
- **Sub-sections**: Net Profit, Provisions, Receivables, Payables, Current Assets/Liabilities, Taxation, Non-Current Assets/Liabilities, Equity
- **Results**: End Cash Balance, Cashbook Balance

### Trial Balance
- All accounts with their debit or credit balances
- Verifies total debits = total credits

### Aging Schedule
- Outstanding receivables or payables bucketed by age
- Brackets: Current (≤30d), 31–90d, 91–180d, 181–270d, 271–365d, 365+d

---

## Reporting Periods

Three states control what transactions can be posted:

| Status | Allowed Transactions |
|--------|---------------------|
| **OPEN** | All transaction types |
| **ADJUSTING** | Journal Entries only |
| **CLOSED** | None (read-only) |

---

## Database & Session Layer

- **SQLAlchemy ORM** with polymorphic inheritance for transactions
- **`AccountingSession`** wraps SQLAlchemy session with custom `add()` and `commit()` that call `validate()` and `validate_delete()` hooks
- **Soft deletes** — `deleted_at` timestamp instead of hard delete; recycled objects tracked in `Recycled` table
- **Entity isolation** — all queries automatically filtered by `entity_id`
- **Multi-tenancy** — single database, multiple entities
- **Event listeners** — hash ledger entries on insert, enforce soft-delete behavior

---

## Project Structure

```
python_accounting/
├── models/
│   ├── account.py          # Account with 16 types, serial codes, balance methods
│   ├── entity.py           # Reporting entity (company)
│   ├── transaction.py      # Base transaction (polymorphic)
│   ├── ledger.py           # Double-entry posting records + hashing
│   ├── line_item.py        # Transaction line items
│   ├── balance.py          # Opening balances from prior periods
│   ├── assignment.py       # Links payments to invoices
│   ├── currency.py         # Currency support
│   ├── category.py         # Account categories
│   ├── tax.py              # Tax rates
│   ├── reporting_period.py # Period lifecycle
│   └── user.py             # System users
├── transactions/
│   ├── journal_entry.py    # Most flexible — simple or compound
│   ├── client_invoice.py   # Credit sales
│   ├── client_receipt.py   # Incoming payments
│   ├── credit_note.py      # Client adjustments
│   ├── cash_sale.py        # Cash sales
│   ├── supplier_bill.py    # Credit purchases
│   ├── supplier_payment.py # Outgoing payments
│   ├── debit_note.py       # Supplier adjustments
│   ├── cash_purchase.py    # Cash purchases
│   └── contra_entry.py     # Bank-to-bank transfers
├── reports/
│   ├── financial_statement.py  # Abstract base
│   ├── income_statement.py     # P&L
│   ├── balance_sheet.py        # Financial position
│   ├── cashflow_statement.py   # Cash movements
│   ├── trial_balance.py        # Debit/credit verification
│   └── aging_schedule.py       # Outstanding by age
├── mixins/
│   ├── isolating.py        # Entity scoping
│   ├── clearing.py         # Transaction clearing
│   ├── assigning.py        # Transaction assignment
│   ├── trading.py          # Account type validation
│   ├── buying.py           # Purchase validation
│   └── selling.py          # Sales validation
├── database/
│   ├── session.py          # AccountingSession
│   ├── session_overrides.py
│   ├── event_listeners.py  # Hashing, soft-delete hooks
│   ├── accounting_functions.py
│   ├── engine.py
│   └── database_init.py
├── exceptions/             # ~20 custom exceptions
├── utils/                  # Helpers
└── config.py               # Reads config.toml
tests/
├── conftest.py             # Fixtures (engine, session, entity, currency)
└── test_*.py               # ~20 test modules covering all models & reports
config.toml                 # Account types, transaction types, report definitions
```

---

## Summary

The system faithfully implements the double-entry bookkeeping method:

1. **Every transaction produces balanced ledger pairs** (debit = credit)
2. **Account types enforce correctness** — you can't post a cash sale to a liability account
3. **Clearing/assignment tracks payment lifecycles** — invoices are marked paid as receipts are assigned
4. **Hash chains guarantee integrity** — posted data can't be silently altered
5. **Reporting period states control access** — closed periods are immutable
6. **Standard financial reports** are generated directly from ledger data
7. **Multi-entity isolation** keeps separate companies' books apart in one database
