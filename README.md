# Northline — ACCT 3343 Financial Analysis

A Streamlit screen combining profitability, value and financial strength for BUY research, with an independent accrual and distress screen for SELL research. Original cream/navy/teal theme.

## Run

Python 3.11 or newer:

```bash
python -m pip install -r requirements.txt
python build_universe.py --target 1000 --pitch YOUR_TICKER
python -m streamlit run app.py
```

The collector uses Yahoo Finance through yfinance. It builds a fresh sector-stratified discovery list of US common equities on NYSE and NASDAQ Global Select, market cap at least USD 300m. Financial Services is excluded. It then processes the largest discovered firms first until 1,000 eligible unique issuers are collected. Metadata and statements are cached locally. Eight bounded concurrent workers reduce repeated metadata calls, and failures are recorded. Re-run to resume, not silently replace existing dates. For a fully fresh screen, move the existing CSV and metadata snapshot to an archive first.

The screener snapshot, raw statement CSVs, info responses and collection log form the audit trail. `universe.csv` contains annual observations, two prior fiscal dates, provenance timestamps and missing-data warnings. Collection is a snapshot, not a live quote stream. Keep the snapshot date visible in submissions.

## Data policy

- Exclude financial services, unknown sector, non-equity instruments, non-USD quotations or financials, stale annual data older than 550 days, and fewer than three aligned annual periods.
- Deduplicate issuer website/name, normalizing class-letter suffixes, and preserve an exclusion log. Review remaining issuer names manually, because Yahoo does not supply a universal issuer identifier.
- Match exact year-end dates across all three statements. Require annual intervals between 300 and 430 days. Preserve missing values. Do not forward-fill financials or substitute zeros.
- Ending total assets scale GPA, STA and SNOA. Beginning assets scale F_SCORE ROA, cash flow and turnover. Prior ratios use the corresponding prior-year balance sheet.
- Common equity is the B/M numerator. Debt includes leases, as the course mapping specifies. Minority and preferred interests remain missing when Yahoo omits them. For SNOA only, reconciled consolidated equity can supply the exact aggregate of common, preferred and minority equity. This is an accounting identity, not a missing-value replacement.
- F_SCORE requires all nine indicators. Missing equity-issuance data is never interpreted as no issuance. Net issuance is used directly, or proceeds minus repurchases when both are present.
- BUY requires all BUY measures and SELL requires all SELL measures. Show separate coverage counts. A row need not be dropped from the entire universe because one technique is unavailable.
- Currency mixing is disallowed. International USD-reporting ADRs can remain; verify issuer-level cap and ADR share ratios against filings before investment use.

## Important course ambiguities

1. Class 3 slide 9 uses coefficients `.012, .014, .033, .006, .999` with decimal ratios; slide 12 demonstrates the same implementation. Standard decimal-ratio Altman coefficients are `1.2, 1.4, 3.3, .6, .999`. Default matches the literal course. The sidebar permits a comparison. Do not describe the course variant as a calibrated probability of bankruptcy. The 1.81 slider default comes from the course quiz; its calibration to the literal coefficient variant is unverified.
2. Class 5 slide 6 says change in ROA `>1`. The conventional signal is `>0`. Default implements the literal slide and the sidebar provides the alternative. Confirm the intended threshold with the professor before submission.
3. Class 5 slide 9 prints CFO ratio `.0112`, but its numerator 1,911,000 divided by 17,019,000 is approximately `.1123`. Calculations use inputs, without copying the arithmetic typo.

## Ranking

Within selected sector/size peers, descending GPA, B/M and F_SCORE ranks are added equally; lowest sum wins. Thresholds apply after peer ranks. The SELL side first sorts by triggered concern count and then by the equally weighted sum of descending STA, descending SNOA and ascending Z ranks. More accrual concerns and lower Z therefore increase SELL priority. Missing components do not receive favorable ranks. Percentiles use the selected peer group and strictly greater comparisons, so ties at a percentile cutoff do not trigger a concern.

Only the underlying sector/size/pitch filters change the peer universe. Financial gates change candidate membership while preserving the peer comparison. Two candidates may share a composite rank; ticker provides deterministic order.

## Submission

The professor asks for three top-level deployment files: `app.py`, `requirements.txt`, `universe.csv`. These are self-contained. Supporting collection code, tests and documentation are development/audit material and need not be uploaded to the deployment repository. Optional `.streamlit/config.toml` applies native theme colours, but the app includes inline styling when deploying only the three files.

Create a public GitHub repository and deploy `app.py` from its `main` branch through Streamlit Community Cloud. Confirm the public URL in a signed-out session. Deployment requires the owner's GitHub and Streamlit authorization. No public URL should be claimed until verified.

Before submitting, identify the pitch company and exclude it permanently in the CSV or collector arguments. Sidebar exclusion is useful during review, but an empty default cannot enforce the assignment restriction across all public sessions. The application warns about this pending condition.

The assignment launch deck says the student writes investment conclusions. Generated explanations are research drafts for Omar to verify and rewrite, not a claim of student authorship. Review the top candidates' filings and business outlook before finalizing those cases.

## Tests

```bash
python -m pip install pytest
python -m pytest -q
```

Tests use explicitly synthetic temporary fixtures, separate from the investment dataset. They cover manual calculations, Empire course examples, missing values, exact SNOA identity, ranking direction, filter combinations, and Streamlit reruns. The collected real-company input audit and actual output coverage belong in `PROJECT_STATUS.md` and `data_audit.json`.
