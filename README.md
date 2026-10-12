# Household Ledger

A local household spending tracker with PDF statement imports, interactive spending and income pie charts, manual bill tracking, member/account dashboards, and optional **local AI category review**.

**No paid AI API, subscription, hosted database, or cloud account is required to run the app.** It runs on your own computer using Python, SQLite and a browser. Ollama is optional. Model downloads, disk space, hardware, internet access and electricity remain your own costs. Model licenses are separate from this application's MIT license.

## What it does

- Imports supported RBC personal chequing PDFs with selectable text.
- Checks extracted deposits, withdrawals, closing balance and available intermediate balances before confirming an import.
- Blocks repeat file contents, even under a different filename, and overlapping statements containing matching transactions.
- Reports by month, quarter, half-year, year or custom dates.
- Shows clickable pie slices and percentages that open their matching transactions.
- Shows five legend entries initially, with Show more / Show less.
- Tracks household members and their Debit, Credit and LOC accounts.
- Lets you choose a category and explicitly Accept it, or Reset an unsaved choice.
- Tracks unpaid/paid bills without adding the same bill twice to spending.
- Offers an "AM I BROKE?" calculator using entered cash, unpaid bills, other expenses and a minimum cushion. It does not forecast income.
- Exports CSV and database backups.

This repository contains **source code and generic configuration only**. It does not include real bank statements, real account details, household identities, transaction databases, personal category rules or screenshots of financial data.

## Requirements

- Python 3.10 or newer: [official downloads](https://www.python.org/downloads/).
- A modern browser.
- Optional: [Ollama](https://ollama.com/download) and a local model that supports structured output.

No Node.js, paid hosting or API key is needed. AI performance depends on the model and available RAM/VRAM; choose a model that fits your computer.

## Install on Windows

Download this repository's ZIP and extract it, or clone it:

```powershell
git clone https://github.com/goldLeader99/household-ledger.git
cd household-ledger
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config.example.json config.json
.\.venv\Scripts\python.exe app.py
```

Open **http://127.0.0.1:8765**. After initial setup, `start.cmd` starts the app and opens your browser. Leave its terminal open while using the app. Close it, or press Ctrl+C, to stop the app.

## Install on macOS / Linux / WSL

```bash
git clone https://github.com/goldLeader99/household-ledger.git
cd household-ledger
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp config.example.json config.json
.venv/bin/python app.py
```

Alternatively, after setup, run `sh start.sh`. Open **http://127.0.0.1:8765**. If `venv` is unavailable on your Linux distribution, install its Python virtual-environment package first.

The project uses normal Python virtual environments; see the [Python Packaging installation guide](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/).

## Configure your household

Edit **config.json** before your first import. This file is ignored by Git and stays private. The app falls back to the generic `config.example.json` when no private config exists.

- `members`: your household member names. `Joint` is reserved for shared expense assignments.
- `accounts`: unique IDs, member owner, display name and `kind` (`Debit`, `Credit` or `LOC`). Keep an account's ID stable after importing data.
- `importer`: `rbc_chequing` for supported RBC chequing accounts, otherwise `null`.
- `ollama.model`: your installed local model.
- `ollama.url`: a local loopback HTTP endpoint; remote/cloud endpoints are rejected.
- `ollama.wsl_distribution`: optional Windows-to-WSL fallback, such as `Ubuntu`; otherwise `null`.
- `category_rules`: optional personal rules; none are included in the public defaults.

Example private rule:

```json
{"merchant": "Walmart", "direction": "debit", "below_cents": 5000, "category": "Groceries"}
```

Amounts use integer cents. `below_cents` is exclusive; this example matches purchases below $50. Omit it to apply the rule at every amount. Direction is `debit`, `credit`, or `any`. Personal configuration rules take priority over remembered merchant categories. Accepted categories are remembered separately for deposits and withdrawals.

Account dashboards use the **source account's owner**. A transaction's separate assignment can be a member or `Joint`.

## Monthly import workflow

1. Select the source account on the Statements page.
2. Choose a supported PDF and click Review import.
3. Check extracted rows, dates, signs and the displayed reconciliation results.
4. Confirm the import only after reviewing it.
5. Click Needs Review to open uncategorised transactions for your selected dates/account.
6. Choose a category, then Accept to save it. Reset discards a draft.

**Current importer limitation:** only the RBC chequing layout above is implemented. Scanned or password-protected PDFs, CIBC chequing, credit-card and LOC statements need dedicated importers. Listing an account does not enable statement parsing for it. A failed reconciliation prevents saving.

Reconciliation is a check, not a guarantee of perfect extraction: matched totals can still coexist with incorrect descriptions or categories. Review your imports.

## Optional Ollama setup: local AI without an API bill

Install Ollama from its [official download page](https://ollama.com/download). Download a local model, for example:

```text
ollama pull qwen3.5:4b
ollama list
```

Start the Ollama application. On systems where its server is not already running:

```text
ollama serve
```

Set `ollama.model` in your private configuration to the exact name shown by `ollama list`. Do not use a cloud model. Local Ollama requests do not need an API key; see the [official local setup instructions](https://docs.ollama.com/quickstart).

If Ollama is in WSL but the app is on Windows, set `wsl_distribution` to the distribution name shown by `wsl --list`. The app first tries the Windows loopback endpoint. If unavailable, it invokes Python inside the configured WSL distribution and calls that distribution's local Ollama API. WSL must have Python 3 and a running Ollama service. No shell interpolation is used for statement descriptions.

## Exactly how AI reviews transactions

**AI does not extract statement amounts or calculate report totals.** PDF extraction and monetary calculations run in Python using integer cents.

When you click Suggest categories with Ollama:

1. The app selects up to 30 uncategorised transactions in the chosen date/account/member range.
2. It sends their internal IDs, descriptions, normalised merchant names and signed amounts to your local Ollama service. Names/addresses from the statement header and complete PDF files are not sent. Descriptions themselves can contain personal information, which is why only local endpoints are allowed.
3. The model returns proposed categories and explanations using a JSON schema. The app checks IDs and category names before displaying them.
4. You can change the proposed category before accepting it.
5. Accept saves the selected category; Reject keeps the transaction unchanged and available for manual review.

Unresolved entries remain in the ledger. AI cannot remove transactions, change dates/amounts or make payments. It can misidentify merchants or suggest wrong categories; its explanation is not proof. The app works fully without Ollama through manual categorisation.

Ollama's [structured-output documentation](https://docs.ollama.com/capabilities/structured-outputs) explains schema-constrained responses. Correct JSON does not imply a correct classification.

## Spending and income definitions

Total spending currently includes **all withdrawals**, including transfers, credit-card repayments and cash withdrawals, shown separately by category. Money in includes all deposits, including transfers and refunds, and its chart distinguishes sources. Net cash flow is money in minus withdrawals.

The app currently has no credit-card importer or cross-account payment matching. If those are added, repayments must be handled carefully to avoid counting the same spending alongside card purchases. The public version does not pretend to implement that matching.

## Privacy, backups and Git hygiene

The server binds to **127.0.0.1 only**. It is a local single-user application with no login system; do not expose it to the internet or use a public tunnel. Other programs/users with access to your machine can potentially access its files or local service.

- `data/ledger.sqlite3` stores records; original PDFs and staged import JSON also stay in `data/`.
- Calculator inputs use the browser's local storage.
- Nothing is uploaded to a bank or paid AI service.
- Files are not encrypted by this app; use operating-system access controls and disk encryption where appropriate.
- Back up the entire data directory while the app is stopped. A database-only backup can also be downloaded from Statements.
- `.gitignore` excludes private config, data, PDFs, databases, exports, screenshots, environment files and virtual environments.
- Run the privacy check before publishing changes. An ignore rule does not remove files that were already tracked or erase older commits.

```text
python scripts/check_public_files.py
```

Optional environment settings: `LEDGER_DATA_DIR` selects a private data directory outside the checkout; `LEDGER_PORT` changes the local app port. If changing the port, open its printed URL rather than the default launcher URL.

## Tests

All tests generate their own **synthetic** statement and temporary database. No real statement fixtures are included.

```text
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## License

[MIT](LICENSE). Python dependencies and downloaded model weights retain their respective licenses.
