---
name: find-and-parse-factsheet
description: |
  Enrich a fund's static data (TER, SRRI/SRI, settlement cycle, cutoff time,
  minimum investment, service providers, dividend policy, …) by locating and
  parsing its UCITS PRIIPS KID or fact sheet PDF, then patching the
  pms_golden_fund document in OpenSearch.

  Use this skill when:
    * the user wants to fill the gaps shown in the "Find an instrument" fund
      detail panel — Fees, Dealing, Risk Rating, Service Providers, Fund
      Profile (replication, benchmark, rebalance frequency) — for a specific
      fund identified by ISIN or short name;
    * the user says something like "enrich fund IE…", "get the KID for X",
      "fill in the fees for the iShares Core MSCI World", "parse the
      factsheet for …".

  Do NOT use this skill for:
    * live NAV / market price / AUM / OHLCV (those come from yfinance via
      `pipeline.gold.fund_yahoo_enrich` — run that script instead);
    * bulk enrichment over thousands of funds — this is per-fund and
      LLM-assisted, intentionally not batched.
---

# find-and-parse-factsheet

LLM-assisted enrichment of one fund's static prospectus-level data from
its public KID / KIID / fact sheet PDF.

## What this skill does

Given an ISIN (or unambiguous name) of an indexed fund, this skill:

1. **Reads the existing `pms_golden_fund` document** so you know the
   issuer, share class, currency, umbrella and management company — the
   anchors you'll use to locate the right document on the provider's
   website.
2. **Finds the KID / KIID / fact sheet URL** for that share class. The
   provider's investor-resources page is the usual entry point. Pages
   that change frequently (BlackRock, Vanguard, Amundi, …) often expose
   per-ISIN PDFs at predictable paths — use the management company name
   from the doc to drive the search.
3. **Downloads + parses the PDF**, extracting the fields below.
4. **Builds a JSON patch** and writes it to disk for the user to review.
5. Only after the user confirms, **PATCHes the OpenSearch document**
   via `POST /pms_golden_fund/_update/<goldenId>`.

Steps 4 and 5 are deliberately separate. KID layouts vary; treat every
parse as a draft until the user has eyeballed it.

## Fields to extract

Map to these FundGolden paths (camelCase, matches the ontology):

| KID label | FundGolden path |
|---|---|
| Total expense ratio / Ongoing charges | `totalExpenseRatio`, `fees.ongoing.totalExpenseRatio` |
| Management fee | `fees.ongoing.managementFee` |
| Entry / exit load | `fees.transactional.entryLoad`, `fees.transactional.exitLoad` |
| Performance fee | `fees.incentive.performanceFee` |
| SRRI (1-7) | `riskRating.srri` |
| SRI (1-7) | `riskRating.sri` |
| Transaction costs PRIIPS | `transactionCostsPRIIPs` |
| Dealing frequency | `dealing.dealingFrequency` |
| Settlement cycle | `dealing.settlementCycle` (e.g. `"T+2"`) |
| Cutoff time | `dealing.cutoffTimeLocal`, `dealing.cutoffTimezone` |
| Minimum initial / subsequent investment | `dealing.minimumInitialInvestment`, `dealing.minimumSubsequentInvestment` |
| Depositary | `serviceProviders.depositary.legalName`, `serviceProviders.depositary.lei` |
| Administrator | `serviceProviders.administrator.legalName` |
| Transfer agent | `serviceProviders.transferAgent.legalName` |
| Auditor | `serviceProviders.auditor.legalName` |
| Benchmark | `benchmarkName`, `benchmarkIdentifier` |
| Replication method | `replicationMethod` (`physicalFull` / `physicalSampling` / `syntheticSwap`) |
| Rebalance frequency | `rebalanceFrequency` |
| Dividend / income policy | `dividendPolicy` (`DISTRIBUTING` / `ACCUMULATING`) |
| Currency hedged share class | `isCurrencyHedged`, `hedgingCurrency` |
| Fund inception date | `inceptionDate` |
| Share class inception | `shareClass.inceptionDate` |
| Holdings count | `holdingsCount` |

Leave a field out of the patch when the KID doesn't carry it. **Don't
guess.**

## Procedure

For an ISIN like `IE00B4L5Y983`:

1. **Read the current doc**:
   ```bash
   curl -sS "http://localhost:9200/pms_golden_fund/_search?q=identifierList.identifier:IE00B4L5Y983&size=1" \
     | python -m json.tool
   ```
   Capture `goldenId`, `managementCompany.legalName`, `umbrella.legalName`,
   `shareClass.name`, `currencyOfDenomination`.

2. **Find the KID** via WebSearch. Bias the query:
   `<umbrella.legalName> <shareClass.name> KID ISIN <ISIN>`
   or
   `site:<provider-domain> <ISIN> KID PDF`.
   For BlackRock iShares the canonical path is something like
   `https://www.ishares.com/.../IE00B4L5Y983/factsheet` or the same path
   ending in `/kiid` — both expose PDFs.

3. **Fetch the PDF**. Prefer the PRIIPS KID over the marketing fact
   sheet: it has SRRI/SRI/costs in regulated form. If both exist, you
   may use them together — fact sheet for benchmark/holdings count, KID
   for the regulated numbers.

4. **Parse**. Use the `anthropic-skills:pdf` skill if available;
   otherwise WebFetch + a simple regex pass works for KIDs which follow
   a tight template. Extract the fields from the table above.

5. **Build a JSON patch file** at
   `data/opensearch/golden/fund/patches/<goldenId>.json`:
   ```json
   {
     "doc": {
       "totalExpenseRatio": 0.002,
       "fees": { "ongoing": { "totalExpenseRatio": 0.002 } },
       "riskRating": { "srri": 6, "sri": 4 },
       "dealing": {
         "dealingFrequency": "daily",
         "settlementCycle": "T+2",
         "cutoffTimeLocal": "15:00",
         "cutoffTimezone": "Europe/Dublin",
         "minimumInitialInvestment": 100000
       },
       "serviceProviders": {
         "depositary": { "legalName": "State Street Custodial Services (Ireland) Limited", "lei": "5493006KMX1IAIVMQI31" },
         "administrator": { "legalName": "State Street Fund Services (Ireland) Limited" }
       },
       "benchmarkName": "MSCI World Index (Net)",
       "replicationMethod": "physicalSampling",
       "rebalanceFrequency": "quarterly"
     }
   }
   ```
   Show the patch to the user. **Wait for confirmation** before
   applying.

6. **Apply** (after user confirms):
   ```bash
   curl -sS -X POST "http://localhost:9200/pms_golden_fund/_update/<goldenId>" \
     -H "Content-Type: application/json" \
     --data-binary "@data/opensearch/golden/fund/patches/<goldenId>.json"
   curl -sS -X POST "http://localhost:9200/pms_golden_fund/_refresh" >/dev/null
   ```
   Then rebuild the search index so the helper reflects any newly
   hoisted fields:
   ```bash
   PYTHONPATH=src python -m pipeline.gold.search_index_build
   ```

7. **Append a `recordMeta.sourceOfTruth` entry** so the audit trail
   stays honest: source = the URL you fetched, `fieldGroup` = the group
   you populated (`fees`, `dealing`, `riskRating`, `serviceProviders`,
   …), `sourceTimestamp` = today.

## Notes on PDF parsing

UCITS KIDs follow the EU PRIIPS template — a 3-page document with
predictable section headings:

- **Section 2** — *What is this product?* → benchmark, replication,
  dividend policy
- **Section 3** — *What are the risks and what could I get in return?*
  → SRI, performance scenarios
- **Section 4** — *What are the costs?* → entry/exit, ongoing, performance,
  PRIIPS transaction costs
- **Section 5** — *Practical information* → depositary, admin, cutoff,
  dealing

Marketing fact sheets are looser — every issuer has their own layout.
Pull benchmark/holdings count from there if the KID is silent. **Don't
infer numbers from charts** — only use values stated in text.

## Quality gates

Refuse to apply the patch if:

- The PDF is a **different share class's** KID (check the ISIN printed
  on the cover).
- The PDF is **out of date** (older than 18 months — KIDs are reissued
  yearly).
- The TER differs from any value already in the doc by more than 20 %.
  In that case present the discrepancy and ask the user.
