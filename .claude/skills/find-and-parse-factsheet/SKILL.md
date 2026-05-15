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
| Total constituent count | `holdingsCount` |
| Holdings as-of date | `holdingsAsOf` |
| Full constituent list (look-through) | `assetAllocation.holdings` — array of `{identifier, name, weight, assetClass}` |
| Region allocation | `assetAllocation.byRegion` — array of `{region, percentage}` |

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

5. **(Optional) Pull the full holdings.** See *Full holdings extraction*
   below. The skill can populate either fact-sheet fields, full holdings,
   or both in one patch.

6. **Build a JSON patch file** at
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
       "rebalanceFrequency": "quarterly",
       "holdingsCount": 1418,
       "holdingsAsOf": "2026-05-12",
       "assetAllocation": {
         "holdings": [
           { "identifier": "US67066G1040", "name": "NVIDIA Corp",   "weight": 0.0529, "assetClass": "EQUITY" },
           { "identifier": "US0378331005", "name": "Apple Inc",     "weight": 0.0418, "assetClass": "EQUITY" }
         ]
       }
     }
   }
   ```
   Show the patch to the user. **Wait for confirmation** before
   applying.

7. **Apply** (after user confirms). The lab ships a small helper that
   wraps the OpenSearch update + refresh and rebuilds the search index
   so any newly populated fields surface in the "Find an instrument" UI:
   ```bash
   PYTHONPATH=src python -m pipeline.gold.apply_fund_patch \
     data/opensearch/golden/fund/patches/<goldenId>.json
   ```
   (Direct curl form: `POST /pms_golden_fund/_update/<goldenId>` with
   the patch as the body, then `POST /pms_golden_fund/_refresh`.)

8. **Append a `recordMeta.sourceOfTruth` entry** so the audit trail
   stays honest: source = the URL you fetched, `fieldGroup` = the group
   you populated (`fees`, `dealing`, `riskRating`, `serviceProviders`,
   `holdings`, …), `sourceTimestamp` = today.

## Full holdings extraction

`pipeline.gold.fund_yahoo_enrich` only gives the top ~10 constituents.
For the **complete** holdings list, the skill is the right surface —
issuer pages aren't programmatically scrapeable (JS-rendered,
obfuscated ajax URLs) but they yield to WebFetch + intelligent parsing.

The umbrella → issuer routing:

| Management company (LEI) | Look here | Hint |
|---|---|---|
| BlackRock Asset Management Ireland Limited | `https://www.ishares.com/uk/individual/en/products/<productID>/.../*holdings*` and any embedded CSV download. Click-through from the iShares product page found by ISIN. | Page has a "Holdings" tab with table + a "Download holdings" link to a CSV. |
| Vanguard Group (Ireland) Limited | `https://www.vanguard.co.uk/professional/product/etf/equity/<ID>/<slug>/portfolio-data` | Holdings table is server-rendered. |
| DWS Investment S.A. (Xtrackers) | `https://etf.dws.com/en-gb/<ISIN>/<slug>/` → "Index, Composition, Performance" tab | Public CSV download under "Composition". |
| Amundi Asset Management / Amundi Luxembourg | `https://www.amundietf.com/en/products/<ISIN>` → "Composition" panel | Top holdings on the page; full list via prospectus or the "All holdings" download. |
| UBS Fund Management (Luxembourg) S.A. | `https://www.ubs.com/lu/en/asset-management/funds/<ISIN>` → "Composition" | Holdings PDF / Excel link. |

### Per-fund procedure

1. Get the fund's `managementCompany.legalName`. Match against the
   table above to pick the right starting URL.
2. WebSearch `site:<provider-domain> <ISIN>` to find the canonical
   product page.
3. WebFetch the page. If the holdings table is embedded in HTML
   (Vanguard, Xtrackers, Amundi often are), parse it directly. If the
   page only exposes a "Download holdings" link, follow that — most
   issuers expose a CSV that's well-formed (Ticker, Name, ISIN, Sector,
   Asset Class, Weight, …).
4. Project each row into `{ identifier, name, weight, assetClass }` per
   the `Holding` entity. Prefer ISIN as the identifier; fall back to
   ticker if ISIN is missing (cash positions often have no ISIN).
5. Capture the snapshot date the issuer states ("Holdings as of …") and
   the total count.

### Holdings-specific quality gates

Refuse to apply the holdings part of the patch if any of these holds:

- The sum of `weight` across rows is outside `[0.95, 1.05]` (issuer
  rounding lives well inside that band; anything else means we mis-
  parsed weights, units, or skipped a chunk of the table).
- The list has fewer than 3 rows for an ETF with `holdingsCount > 10`.
- The "Holdings as of" date is older than 30 days.
- More than 1 % of rows lack an identifier of any kind.

### Holdings patch shape

Holdings live under `assetAllocation.holdings`; the total constituent
count is at the top level under `holdingsCount` so the frontend can
render "10 of 1418" when only a top-N projection is available. The
patch fragment for holdings looks like:

```json
"doc": {
  "holdingsCount": 1418,
  "holdingsAsOf": "2026-05-12",
  "assetAllocation": {
    "holdings": [
      { "identifier": "US67066G1040", "name": "NVIDIA Corp",   "weight": 0.0529, "assetClass": "EQUITY" },
      …
    ]
  }
}
```

If you also derive sector / region / asset-class roll-ups from the
holdings, include them under `assetAllocation.bySector`,
`assetAllocation.byRegion`, `assetAllocation.byAssetClass` — same patch.

## Full holdings: prefer a live parser over downloaded files

`pipeline.gold.fund_yahoo_enrich` fills `assetAllocation.holdings` with
yfinance's top-10 projection. For the **complete constituent list**,
prefer parsing the issuer's live product page over the daily holdings
CSV files: the CSV downloads are typically T-1 and the page often has
intraday updates plus a stable HTML table you can scrape. Pattern: for
each fund's `managementCompany.legalName` (BlackRock Asset Management
Ireland Limited → iShares; Vanguard Group (Ireland) Limited → Vanguard;
…), navigate to the issuer's product page for that ISIN, parse the
holdings table, and PATCH `assetAllocation.holdings` with the full
list. The ontology already accepts an arbitrary-length array — set
`holdingsCount` to the total even when you write only the top N.

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
