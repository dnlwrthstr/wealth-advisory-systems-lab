import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelOrder,
  fetchInstrumentDocument,
  fetchInstrumentTypes,
  fetchOrder,
  fetchReference,
  findInstruments,
  listPortfolioOrders,
  submitOrder,
} from "./services/api";

// Build the per-result Instrument-shaped object expected by QuickOrderDialog
// from a search-hit. The hit doesn't carry a `price` field (the helper index
// stores no live market data), so we leave it null — order dialog will fall
// back to its limit-price input.
function hitToInstrument(hit) {
  const isin =
    (hit.identifiers || []).find((id) => (id.type || "").toLowerCase() === "isin")?.identifier
    || "";
  return {
    id: hit.document_id,
    isin,
    name: hit.long_name,
    shortName: hit.short_name || hit.ticker || "",
    type: hit.ow_type,
    currency: hit.currency || "",
    price: null,
    exchange: hit.venue_mic,
    country: hit.country,
    sector: null,
    description: hit.issuer_legal_name || "",
  };
}

const TYPE_TABS = [
  { id: "all", label: "All" },
  { id: "equity", label: "Equity" },
  { id: "simpleBond", label: "Bond" },
  { id: "fund", label: "Fund" },
];

// ─── Find-an-instrument view ────────────────────────────────────────────────

export default function InstrumentsApp() {
  const [identifier, setIdentifier] = useState("");
  const [name, setName] = useState("");
  const [typeTab, setTypeTab] = useState("all");
  const [currencyFilter, setCurrencyFilter] = useState("");
  const [countryFilter, setCountryFilter] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const [currencies, setCurrencies] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [showOrder, setShowOrder] = useState(false);

  const debounceRef = useRef(null);

  useEffect(() => {
    fetchInstrumentTypes().catch(() => {}); // keep the call to warm the type index
    fetchReference().then((ref) => setCurrencies(ref.currency ?? [])).catch(() => {});
  }, []);

  const doSearch = useCallback(
    (params) => {
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(async () => {
        setLoading(true);
        setError(null);
        try {
          setResults(await findInstruments(params));
        } catch (err) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
      }, 250);
    },
    []
  );

  useEffect(() => {
    doSearch({
      identifier,
      name,
      type: typeTab,
      currency: currencyFilter || null,
      country: countryFilter || null,
      limit: 10,
    });
  }, [identifier, name, typeTab, currencyFilter, countryFilter, doSearch]);

  const items = results?.items ?? [];
  const total = results?.total ?? 0;
  const selected = items.find((h) => h.document_id === selectedId) || null;

  // Fetch the full per-security source whenever the selection changes.
  const [docSource, setDocSource] = useState(null);
  const [docLoading, setDocLoading] = useState(false);
  useEffect(() => {
    if (!selected) {
      setDocSource(null);
      return;
    }
    let alive = true;
    setDocLoading(true);
    fetchInstrumentDocument(selected.scope, selected.document_id)
      .then((d) => {
        if (alive) setDocSource(d.source);
      })
      .catch(() => {
        if (alive) setDocSource(null);
      })
      .finally(() => {
        if (alive) setDocLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [selected?.scope, selected?.document_id]);

  return (
    <div className="finder">
      <header className="finder-header">
        <p className="eyebrow"><span className="finder-icon">⌕</span> INSTRUMENT SEARCH</p>
        <h1 className="finder-title">Find an instrument</h1>
        <p className="finder-sub">
          Search the golden records across equity, bond, and fund indices. Use the
          type tabs to narrow, or leave on "All" to search everywhere at once.
          Advanced filters adapt to the selected type.
        </p>

        <div className="finder-tabs" role="tablist">
          {TYPE_TABS.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              type="button"
              className={`finder-tab${typeTab === tab.id ? " active" : ""}`}
              onClick={() => setTypeTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="finder-fields finder-fields-2">
          <label className="finder-field">
            <span className="finder-field-label">Identifier</span>
            <span className="finder-input-wrap">
              <span className="finder-input-icon mono">#</span>
              <input
                type="search"
                value={identifier}
                placeholder="ISIN / ticker / valor / CUSIP"
                onChange={(e) => setIdentifier(e.target.value)}
              />
            </span>
          </label>
          <label className="finder-field">
            <span className="finder-field-label">Name</span>
            <span className="finder-input-wrap">
              <span className="finder-input-icon">⌕</span>
              <input
                type="search"
                value={name}
                placeholder="Short or long name"
                onChange={(e) => setName(e.target.value)}
              />
            </span>
          </label>
        </div>

        <button
          type="button"
          className="finder-advanced-toggle"
          onClick={() => setAdvancedOpen((v) => !v)}
        >
          {advancedOpen ? "▾" : "▸"} Advanced filters
        </button>
        {advancedOpen && (
          <div className="finder-advanced">
            <label>
              Currency
              <select value={currencyFilter} onChange={(e) => setCurrencyFilter(e.target.value)}>
                <option value="">Any</option>
                {currencies.map((c) => (
                  <option key={c.value} value={c.value}>{c.value} — {c.label}</option>
                ))}
              </select>
            </label>
            <label>
              Country (ISO-2)
              <input
                type="text"
                maxLength={2}
                placeholder="e.g. CH"
                value={countryFilter}
                onChange={(e) => setCountryFilter(e.target.value.toUpperCase())}
              />
            </label>
            <p className="finder-advanced-note">
              Type-specific filters (sector for equities, coupon range for bonds, fund
              sub-type for funds) coming next; the helper index already carries the
              fields.
            </p>
          </div>
        )}
      </header>

      {error && <p className="finder-error">{error}</p>}

      <section className="finder-results">
        <div className="finder-results-header">
          <span className="finder-count">
            {loading
              ? "Searching…"
              : `${Math.min(total, 10)} of ${total} result${total === 1 ? "" : "s"}`}
          </span>
          <span className="finder-index-name">Index: pms_golden_instrumentsearch</span>
        </div>

        {!loading && items.length === 0 ? (
          <p className="finder-empty">No instruments matched.</p>
        ) : (
          <ResultTable
            items={items}
            typeTab={typeTab}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        )}
      </section>

      {selected && (
        <DetailSection
          hit={selected}
          source={docSource}
          loading={docLoading}
          onClose={() => setSelectedId(null)}
          onTrade={() => setShowOrder(true)}
        />
      )}

      {showOrder && selected && (
        <QuickOrderDialog
          instrument={hitToInstrument(selected)}
          onClose={() => setShowOrder(false)}
        />
      )}
    </div>
  );
}

// ─── Result table (compact, scrollable, type-aware columns) ─────────────────

function isinFor(hit) {
  return (hit.identifiers || []).find((id) => (id.type || "").toLowerCase() === "isin")?.identifier || "";
}

function labelForType(t) {
  return ({ equity: "Equity", simpleBond: "Bond", fund: "Fund" })[t] || t;
}

function fmtPct(decimal) {
  if (decimal == null) return "—";
  return `${(decimal * 100).toFixed(3)} %`;
}

// Columns keyed by the active type tab. Each entry: {label, render(hit)}.
const COLUMNS = {
  all: [
    { key: "isin",   label: "ISIN / ID",   render: (h) => <span className="mono">{isinFor(h) || h.document_id}</span> },
    { key: "valor",  label: "Valor",       render: (h) => <span className="mono">{h.valor || "—"}</span> },
    { key: "type",   label: "Type",        render: (h) => <span className="finder-row-chip">{labelForType(h.ow_type)}</span> },
    { key: "name",   label: "Name",        render: (h) => <span className="finder-row-name">{h.long_name}</span>, wide: true },
    { key: "ccy",    label: "CCY",         render: (h) => <span className="mono">{h.currency || "—"}</span> },
  ],
  equity: [
    { key: "isin",   label: "ISIN",        render: (h) => <span className="mono">{isinFor(h) || "—"}</span> },
    { key: "valor",  label: "Valor",       render: (h) => <span className="mono">{h.valor || "—"}</span> },
    { key: "ticker", label: "Ticker",      render: (h) => <span className="mono">{h.ticker || "—"}</span> },
    { key: "name",   label: "Name",        render: (h) => <span className="finder-row-name">{h.long_name}</span>, wide: true },
    { key: "sector", label: "Sector",      render: (h) => h.sector || "—" },
    { key: "ccy",    label: "CCY",         render: (h) => <span className="mono">{h.currency || "—"}</span> },
    { key: "mic",    label: "Venue",       render: (h) => <span className="mono">{h.venue_mic || "—"}</span> },
    { key: "country",label: "Country",     render: (h) => <span className="mono">{h.country || "—"}</span> },
  ],
  simpleBond: [
    { key: "isin",   label: "ISIN",        render: (h) => <span className="mono">{isinFor(h) || "—"}</span> },
    { key: "valor",  label: "Valor",       render: (h) => <span className="mono">{h.valor || "—"}</span> },
    { key: "name",   label: "Name",        render: (h) => <span className="finder-row-name">{h.long_name}</span>, wide: true },
    { key: "issuer", label: "Issuer",      render: (h) => h.issuer_legal_name || "—" },
    { key: "coupon", label: "Coupon",      render: (h) => <span className="mono">{fmtPct(h.coupon_rate)}</span> },
    { key: "mat",    label: "Maturity",    render: (h) => <span className="mono">{h.maturity_date || "—"}</span> },
    { key: "rating", label: "Rating",      render: (h) => <span className="finder-row-chip">{h.issuer_rating || "—"}</span> },
    { key: "ccy",    label: "CCY",         render: (h) => <span className="mono">{h.currency || "—"}</span> },
  ],
  fund: [
    { key: "isin",   label: "ISIN",        render: (h) => <span className="mono">{isinFor(h) || "—"}</span> },
    { key: "valor",  label: "Valor",       render: (h) => <span className="mono">{h.valor || "—"}</span> },
    { key: "name",   label: "Share Class", render: (h) => <span className="finder-row-name">{h.long_name}</span>, wide: true },
    { key: "sub",    label: "Sub-fund",    render: (h) => h.sub_fund_name || "—" },
    { key: "umb",    label: "Umbrella",    render: (h) => h.umbrella_name || h.issuer_legal_name || "—" },
    { key: "sub_t",  label: "Sub-type",    render: (h) => <span className="finder-row-chip">{h.fund_sub_type || "—"}</span> },
    { key: "div",    label: "Policy",      render: (h) => h.dividend_policy || "—" },
    { key: "ccy",    label: "CCY",         render: (h) => <span className="mono">{h.currency || "—"}</span> },
  ],
};

function ResultTable({ items, typeTab, selectedId, onSelect }) {
  const cols = COLUMNS[typeTab] || COLUMNS.all;
  return (
    <div className="finder-table-wrap">
      <table className="finder-table">
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c.key} className={c.wide ? "wide" : ""}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((hit) => (
            <tr
              key={`${hit.scope}:${hit.document_id}`}
              className={selectedId === hit.document_id ? "selected" : ""}
              onClick={() => onSelect(hit.document_id)}
            >
              {cols.map((c) => (
                <td key={c.key} className={c.wide ? "wide" : ""}>{c.render(hit)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Inline detail section (type-aware sub-panels) ──────────────────────────

const EM_DASH = "—";

function val(v) {
  if (v === null || v === undefined || v === "") return EM_DASH;
  return v;
}

function fmtPctVal(v) {
  if (v === null || v === undefined) return EM_DASH;
  return `${(v * 100).toFixed(3)} %`;
}

function fmtMoney(amount, currency) {
  if (amount == null) return EM_DASH;
  const symbol = ({ USD: "$", EUR: "€", GBP: "£", CHF: "CHF", JPY: "¥" })[currency] || "";
  const sign = symbol || currency || "";
  return `${sign}${Number(amount).toLocaleString("en-CH", { maximumFractionDigits: 2 })}`;
}

function Subpanel({ icon, title, children, span }) {
  return (
    <section className={`subpanel${span === 2 ? " span-2" : ""}`}>
      <h4 className="subpanel-title">
        {icon && <span className="subpanel-icon">{icon}</span>}
        {title}
      </h4>
      <div className="subpanel-body">{children}</div>
    </section>
  );
}

function KV({ children }) {
  return <dl className="subpanel-dl">{children}</dl>;
}

function Row({ label, value }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value === EM_DASH || value === null || value === undefined ? <span className="muted">{EM_DASH}</span> : value}</dd>
    </>
  );
}

function IdentifierChips({ identifiers }) {
  const list = identifiers || [];
  return (
    <section className="subpanel span-2">
      <h4 className="subpanel-title">
        <span className="subpanel-icon mono">#</span>
        Identifiers
        <span className="subpanel-count">{list.length} total</span>
      </h4>
      <div className="subpanel-body">
        <div className="id-chip-grid">
          {list.map((id) => (
            <span key={`${id.type}:${id.identifier}`} className="id-chip">
              <span className="id-chip-scheme">{(id.type || "").toUpperCase()}</span>
              <span className="id-chip-value mono">{id.identifier}</span>
            </span>
          ))}
          {list.length === 0 && <span className="muted">{EM_DASH}</span>}
        </div>
      </div>
    </section>
  );
}

function HierarchyStep({ n, label, primary, lines }) {
  return (
    <li className="hierarchy-step">
      <span className="hierarchy-num">{n}</span>
      <div>
        <p className="hierarchy-label">{label}</p>
        <p className="hierarchy-primary">{primary || EM_DASH}</p>
        {lines && lines.filter(Boolean).map((line, i) => (
          <p key={i} className="hierarchy-line">{line}</p>
        ))}
      </div>
    </li>
  );
}

function FundHierarchy({ source }) {
  const promoter = source.promoter || {};
  const mc = source.managementCompany || {};
  const umbrella = source.umbrella || {};
  const subFund = source.subFund || {};
  const shareClass = source.shareClass || {};
  const isin = (source.identifierList || []).find(
    (id) => (id.type || "").toLowerCase() === "isin"
  )?.identifier;
  return (
    <section className="subpanel span-2">
      <h4 className="subpanel-title">
        <span className="subpanel-icon">⛁</span>
        Corporate Hierarchy
      </h4>
      <ol className="hierarchy-list">
        <HierarchyStep n={1} label="Promoter" primary={promoter.legalName} />
        <HierarchyStep
          n={2}
          label="Management Company"
          primary={mc.legalName}
          lines={[
            mc.lei && `LEI ${mc.lei}`,
            mc.domicileCountry && `Domicile ${mc.domicileCountry}`,
          ]}
        />
        <HierarchyStep
          n={3}
          label="Umbrella"
          primary={umbrella.legalName}
          lines={[
            umbrella.lei && `LEI ${umbrella.lei}`,
            [umbrella.legalStructure, umbrella.domicileCountry && `(${umbrella.domicileCountry})`]
              .filter(Boolean)
              .join(" · "),
          ]}
        />
        <HierarchyStep
          n={4}
          label="Sub-fund"
          primary={subFund.name}
          lines={[subFund.inceptionDate && `Inception ${subFund.inceptionDate}`]}
        />
        <HierarchyStep
          n={5}
          label="Share Class"
          primary={shareClass.name}
          lines={[
            [shareClass.type, shareClass.hedged === false ? "unhedged" : (shareClass.hedged ? "hedged" : null), shareClass.currency]
              .filter(Boolean)
              .join(" · "),
            (shareClass.isin || isin) && `ISIN ${shareClass.isin || isin}`,
          ]}
        />
      </ol>
    </section>
  );
}

function FundDetail({ source }) {
  const mc = source.managementCompany || {};
  const primary = source.primaryListing || {};
  const subFund = source.subFund || {};
  const shareClass = source.shareClass || {};
  const umbrella = source.umbrella || {};
  const fees = source.fees || {};
  const dealing = source.dealing || {};
  const risk = source.riskRating || {};
  const md = source.marketData || {};
  const sp = source.serviceProviders || {};

  return (
    <>
      <IdentifierChips identifiers={source.identifierList} />
      <FundHierarchy source={source} />

      <Subpanel icon="⌂" title="Management Company">
        <KV>
          <Row label="Legal name" value={val(mc.legalName)} />
          <Row label="Type" value={<span className="mono">{val(mc.organisationType)}</span>} />
          <Row label="LEI" value={<span className="mono">{val(mc.lei)}</span>} />
          <Row label="Domicile" value={val(mc.domicileCountry)} />
          <Row label="HQ country" value={val(mc.headquartersCountry)} />
          <Row label="ManCo ID" value={<span className="mono">{val(mc.organisationId)}</span>} />
        </KV>
      </Subpanel>

      <Subpanel icon="◎" title="Primary Listing">
        <KV>
          <Row label="MIC" value={<span className="mono">{val(primary.mic)}</span>} />
          <Row label="Ticker" value={<span className="mono">{val(primary.ticker)}</span>} />
          <Row label="Listing currency" value={<span className="mono">{val(primary.listingCurrency)}</span>} />
          <Row label="Status" value={val(primary.status)} />
          <Row label="Venue country" value={val(primary.venueCountry)} />
          <Row label="First trading" value={<span className="mono">{val(primary.firstTradingDate)}</span>} />
          <Row label="Primary" value={primary.isPrimary === true ? "Yes" : primary.isPrimary === false ? "No" : EM_DASH} />
        </KV>
      </Subpanel>

      <Subpanel icon="🏷" title="Classification">
        <KV>
          <Row label="Asset class" value={val(source.assetClass)} />
          <Row label="Asset class ID" value={<span className="mono">{val(source.assetClassId)}</span>} />
          <Row label="Fund subtype" value={val(source.fundSubType)} />
          <Row label="CFI code" value={<span className="mono">{val(source.cfiCode)}</span>} />
        </KV>
      </Subpanel>

      <Subpanel icon="⛁" title="Fund Profile">
        <KV>
          <Row label="Subtype" value={val(source.fundSubType)} />
          <Row label="Primary exposure" value={val(source.primaryAssetClassExposure)} />
          <Row label="Sub-fund" value={val(subFund.name)} />
          <Row label="Share class" value={val(shareClass.name)} />
          <Row label="Share class type" value={val(shareClass.type)} />
          <Row label="Benchmark" value={val(source.benchmarkName)} />
          <Row label="Replication" value={val(source.replicationMethod)} />
          <Row label="Rebalance" value={val(source.rebalanceFrequency)} />
          <Row label="Legal framework" value={val(source.legalFramework)} />
          <Row label="Legal structure" value={val(source.legalStructure)} />
          <Row label="Dividend policy" value={val(source.dividendPolicy)} />
          <Row label="Umbrella" value={val(umbrella.legalName)} />
          <Row label="Inception" value={<span className="mono">{val(source.inceptionDate || subFund.inceptionDate)}</span>} />
          <Row
            label="Currency hedged"
            value={source.isCurrencyHedged === true ? "Yes" : source.isCurrencyHedged === false ? "No" : EM_DASH}
          />
        </KV>
      </Subpanel>

      <Subpanel icon="%" title="Fees">
        <KV>
          <Row label="TER" value={fmtPctVal(fees?.ongoing?.totalExpenseRatio ?? source.totalExpenseRatio)} />
          <Row label="Ongoing charges" value={fmtPctVal(fees?.ongoing?.totalExpenseRatio ?? source.totalExpenseRatio)} />
        </KV>
      </Subpanel>

      <Subpanel icon="⤳" title="Dealing">
        <KV>
          <Row label="Frequency" value={val(dealing.dealingFrequency)} />
          <Row label="Settlement" value={val(dealing.settlementCycle)} />
          <Row label="Cutoff" value={[dealing.cutoffTimeLocal, dealing.cutoffTimezone].filter(Boolean).join(" ") || EM_DASH} />
          <Row label="Min initial" value={fmtMoney(dealing.minimumInitialInvestment, source.currencyOfDenomination)} />
          <Row label="Min subsequent" value={fmtMoney(dealing.minimumSubsequentInvestment, source.currencyOfDenomination)} />
        </KV>
      </Subpanel>

      <Subpanel icon="⚠" title="Risk Rating">
        <KV>
          <Row label="SRRI (1–7)" value={val(risk.srri)} />
          <Row label="SRI (1–7)" value={val(risk.sri)} />
          <Row label="PRIIPS transaction costs" value={fmtPctVal(source.transactionCostsPRIIPs)} />
          <Row label="Portfolio turnover (annual)" value={fmtPctVal(source.portfolioTurnoverPctAnnual)} />
        </KV>
      </Subpanel>

      <Subpanel icon="◷" title="NAV & AUM">
        <KV>
          <Row label="NAV" value={fmtMoney(md.nav?.value, md.nav?.currency || source.currencyOfDenomination)} />
          <Row label="Market price" value={fmtMoney(md.marketPrice?.value, md.marketPrice?.currency || source.currencyOfDenomination)} />
          <Row label="AUM" value={fmtMoney(md.aum?.amount, md.aum?.currency || source.currencyOfDenomination)} />
          <Row label="Shares in issue" value={md.sharesInIssue != null ? Number(md.sharesInIssue).toLocaleString() : EM_DASH} />
          <Row label="Premium / discount" value={fmtPctVal(md.premiumDiscount)} />
          <Row label="Source MIC" value={<span className="mono">{val(md.sourceMic)}</span>} />
        </KV>
      </Subpanel>

      <Subpanel icon="🛠" title="Service Providers">
        <KV>
          <Row label="Depositary" value={val(sp.depositary?.legalName || sp.depositary)} />
          <Row label="Administrator" value={val(sp.administrator?.legalName || sp.administrator)} />
          <Row label="Transfer agent" value={val(sp.transferAgent?.legalName || sp.transferAgent)} />
          <Row label="Auditor" value={val(sp.auditor?.legalName || sp.auditor)} />
        </KV>
      </Subpanel>

      <Subpanel icon="📈" title="Market Data">
        <KV>
          <Row label="Open" value={md.open != null ? md.open : EM_DASH} />
          <Row label="High" value={md.high != null ? md.high : EM_DASH} />
          <Row label="Low" value={md.low != null ? md.low : EM_DASH} />
          <Row label="Close" value={md.close != null ? md.close : EM_DASH} />
          <Row label="Volume" value={md.volume != null ? Number(md.volume).toLocaleString() : EM_DASH} />
          <Row label="Source MIC" value={<span className="mono">{val(md.sourceMic)}</span>} />
        </KV>
      </Subpanel>

      <AllocationPanel allocation={source.assetAllocation} />
      <HoldingsPanel source={source} allocation={source.assetAllocation} />
      <ProvenancePanel recordMeta={source.recordMeta} />
    </>
  );
}

function AllocationPanel({ allocation }) {
  const byAsset = (allocation?.byAssetClass || []).filter((r) => r.percentage > 0);
  const bySector = (allocation?.bySector || []).filter((r) => r.percentage > 0);
  const byRegion = (allocation?.byRegion || []).filter((r) => r.percentage > 0);
  const empty = byAsset.length === 0 && bySector.length === 0 && byRegion.length === 0;
  return (
    <Subpanel icon="◐" title="Asset Allocation">
      {empty && <p className="muted">{EM_DASH}</p>}
      {byAsset.length > 0 && <AllocationBars title="By asset class" rows={byAsset.map((r) => [r.type, r.percentage])} />}
      {byRegion.length > 0 && <AllocationBars title="By region" rows={byRegion.map((r) => [r.region, r.percentage])} />}
      {bySector.length > 0 && <AllocationBars title="By sector" rows={bySector.map((r) => [r.sector, r.percentage])} />}
    </Subpanel>
  );
}

function AllocationBars({ title, rows }) {
  // Sort descending; cap to 8 rows; collapse the rest into "Other".
  const sorted = [...rows].sort((a, b) => b[1] - a[1]);
  const top = sorted.slice(0, 8);
  const tail = sorted.slice(8);
  if (tail.length) {
    const tailSum = tail.reduce((s, [, w]) => s + w, 0);
    if (tailSum > 0) top.push(["Other", tailSum]);
  }
  return (
    <div className="alloc-block">
      <p className="alloc-title">{title}</p>
      <ul className="alloc-bars">
        {top.map(([label, pct]) => (
          <li key={label}>
            <span className="alloc-label">{label}</span>
            <span className="alloc-bar-wrap">
              <span className="alloc-bar" style={{ width: `${Math.min(100, pct * 100)}%` }} />
            </span>
            <span className="alloc-pct mono">{(pct * 100).toFixed(2)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ProvenancePanel({ recordMeta }) {
  const [open, setOpen] = useState(true);
  if (!recordMeta) return null;
  const sources = recordMeta.sourceOfTruth || [];
  return (
    <section className="subpanel span-2 provenance">
      <button
        type="button"
        className="subpanel-title provenance-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="subpanel-icon">{open ? "▾" : "▸"}</span>
        Record Provenance
      </button>
      {open && (
        <div className="subpanel-body">
          <KV>
            <Row label="Schema version" value={<span className="mono">{val(recordMeta.schemaVersion)}</span>} />
            <Row label="Golden as-of" value={<span className="mono">{val(recordMeta.goldenAsOf)}</span>} />
            <Row label="Ingestion run" value={<span className="mono">{val(recordMeta.ingestionRunId)}</span>} />
            <Row label="Active" value={recordMeta.isActive === true ? "Yes" : recordMeta.isActive === false ? "No" : EM_DASH} />
          </KV>
          <p className="provenance-section-title">Source of truth</p>
          {sources.length === 0 ? (
            <p className="muted">{EM_DASH}</p>
          ) : (
            <ul className="provenance-list">
              {sources.map((e, i) => (
                <li key={`${e.fieldGroup}:${e.source}:${i}`}>
                  <span className="provenance-field">{e.fieldGroup}</span>
                  <span className="provenance-source">
                    {e.source}
                    {e.sourceTimestamp ? <span className="muted"> ({e.sourceTimestamp})</span> : null}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

function HoldingsPanel({ source, allocation }) {
  const holdings = (allocation?.holdings || []).filter((h) => h.weight > 0);
  const totalCount = source?.holdingsCount;
  const subtitle = holdings.length
    ? (totalCount && totalCount > holdings.length
        ? `${holdings.length} of ${totalCount}`
        : `${holdings.length}`)
    : "";
  return (
    <Subpanel icon="⛁" title={`Holdings (Look-through)${subtitle ? ` · ${subtitle}` : ""}`} span={2}>
      {holdings.length === 0 ? (
        <p className="muted">{EM_DASH}</p>
      ) : (
        <div className={`holdings-scroll${holdings.length > 10 ? " is-scrollable" : ""}`}>
          <table className="holdings-table">
            <thead>
              <tr>
                <th className="r">#</th>
                <th>Identifier</th>
                <th>Name</th>
                <th>Asset class</th>
                <th className="r">Weight</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h, i) => (
                <tr key={`${h.identifier}-${i}`}>
                  <td className="r mono">{i + 1}</td>
                  <td className="mono">{h.identifier}</td>
                  <td>{h.name}</td>
                  <td>{h.assetClass || EM_DASH}</td>
                  <td className="r mono">{(h.weight * 100).toFixed(3)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Subpanel>
  );
}

function EquityDetail({ source }) {
  const issuer = source.issuer || {};
  const primary = source.primaryListing || {};
  const industry = source.industrySector || {};
  const md = source.marketData || {};
  const kf = source.keyFigures || {};
  return (
    <>
      <IdentifierChips identifiers={source.identifierList} />

      <Subpanel icon="⛁" title="Issuer">
        <KV>
          <Row label="Legal name" value={val(issuer.legalName)} />
          <Row label="LEI" value={<span className="mono">{val(issuer.lei)}</span>} />
          <Row label="Type" value={val(issuer.issuerType)} />
          <Row label="Domicile" value={val(issuer.domicileCountry)} />
          <Row label="HQ country" value={val(issuer.headquartersCountry)} />
          <Row label="Ultimate parent" value={<span className="mono">{val(issuer.ultimateParentLei)}</span>} />
        </KV>
      </Subpanel>

      <Subpanel icon="🏷" title="Classification">
        <KV>
          <Row label="Asset class" value={val(source.assetClass)} />
          <Row label="Asset class ID" value={<span className="mono">{val(source.assetClassId)}</span>} />
          <Row label="Equity sub-type" value={val(source.equitySubType)} />
          <Row label="CFI" value={<span className="mono">{val(source.cfiCode)}</span>} />
          <Row label="Sector" value={val(industry.sectorLabel || industry.canonicalLabel)} />
          <Row label="Industry" value={val(industry.industryLabel)} />
        </KV>
      </Subpanel>

      <Subpanel icon="◎" title="Primary Listing">
        <KV>
          <Row label="MIC" value={<span className="mono">{val(primary.mic)}</span>} />
          <Row label="Ticker" value={<span className="mono">{val(primary.ticker)}</span>} />
          <Row label="Listing currency" value={<span className="mono">{val(primary.listingCurrency)}</span>} />
          <Row label="Status" value={val(primary.status)} />
          <Row label="First trading" value={<span className="mono">{val(primary.firstTradingDate)}</span>} />
          <Row label="Country of incorporation" value={val(source.incorporationCountry)} />
        </KV>
      </Subpanel>

      <Subpanel icon="📈" title="Market Data">
        <KV>
          <Row label="Last price" value={md.lastTradePrice?.value != null ? md.lastTradePrice.value : EM_DASH} />
          <Row label="Open" value={md.open != null ? md.open : EM_DASH} />
          <Row label="High" value={md.high != null ? md.high : EM_DASH} />
          <Row label="Low" value={md.low != null ? md.low : EM_DASH} />
          <Row label="Close" value={md.close != null ? md.close : EM_DASH} />
          <Row label="Volume" value={md.volume != null ? Number(md.volume).toLocaleString() : EM_DASH} />
        </KV>
      </Subpanel>

      <Subpanel icon="$" title="Key Figures">
        <KV>
          <Row label="Market cap" value={fmtMoney(kf.marketCapitalization?.amount, kf.marketCapitalization?.currency)} />
          <Row label="EPS" value={kf.earningsPerShare?.amount != null ? kf.earningsPerShare.amount : EM_DASH} />
          <Row label="P/E" value={kf.priceToEarningsRatio != null ? kf.priceToEarningsRatio : EM_DASH} />
          <Row label="Volatility (β)" value={kf.volatility != null ? kf.volatility : EM_DASH} />
          <Row label="Shares outstanding" value={source.sharesOutstanding != null ? Number(source.sharesOutstanding).toLocaleString() : EM_DASH} />
          <Row label="Dividend yield" value={fmtPctVal(source.dividendPolicy?.dividendYield)} />
        </KV>
      </Subpanel>

      <ProvenancePanel recordMeta={source.recordMeta} />
    </>
  );
}

function BondDetail({ source }) {
  const issuer = source.issuer || {};
  const primary = source.primaryListing || {};
  const credit = issuer.creditProfile || {};
  const ratings = credit.issuerRatings || [];
  return (
    <>
      <IdentifierChips identifiers={source.identifierList} />

      <Subpanel icon="⛁" title="Issuer">
        <KV>
          <Row label="Legal name" value={val(issuer.legalName)} />
          <Row label="LEI" value={<span className="mono">{val(issuer.lei)}</span>} />
          <Row label="Type" value={val(issuer.issuerType)} />
          <Row label="Domicile" value={val(issuer.domicileCountry)} />
          <Row label="HQ country" value={val(issuer.headquartersCountry)} />
          <Row label="Ultimate parent" value={<span className="mono">{val(issuer.ultimateParentLei)}</span>} />
        </KV>
      </Subpanel>

      <Subpanel icon="🏷" title="Bond Profile">
        <KV>
          <Row label="Asset class" value={val(source.assetClass)} />
          <Row label="Bond sub-type" value={val(source.bondSubType)} />
          <Row label="Seniority" value={val(source.seniority)} />
          <Row label="Country of risk" value={val(source.countryOfRisk)} />
          <Row label="Currency" value={<span className="mono">{val(source.currencyOfDenomination)}</span>} />
          <Row label="Coupon type" value={val(source.couponType)} />
          <Row label="Current coupon" value={fmtPctVal(source.currentCouponRate)} />
          <Row label="Maturity" value={<span className="mono">{val(source.maturityDate)}</span>} />
          <Row label="Min denomination" value={source.minimumDenomination != null ? Number(source.minimumDenomination).toLocaleString() : EM_DASH} />
          <Row label="Lifecycle" value={val(source.lifecycleStatus)} />
        </KV>
      </Subpanel>

      <Subpanel icon="★" title="Credit Profile">
        {ratings.length === 0 ? (
          <p className="muted">{EM_DASH}</p>
        ) : (
          <ul className="rating-list">
            {ratings.map((r, i) => {
              const obj = typeof r === "string" ? { rating: r } : r;
              return (
                <li key={i}>
                  <span className="finder-row-chip">{val(obj.rating)}</span>
                  <span className="muted">
                    {[obj.agency, obj.ratingType, obj.scale, obj.outlook].filter(Boolean).join(" · ") || ""}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </Subpanel>

      <Subpanel icon="◎" title="Primary Listing">
        <KV>
          <Row label="MIC" value={<span className="mono">{val(primary.mic)}</span>} />
          <Row label="Listing currency" value={<span className="mono">{val(primary.listingCurrency)}</span>} />
          <Row label="Status" value={val(primary.status)} />
          <Row label="First trading" value={<span className="mono">{val(primary.firstTradingDate)}</span>} />
        </KV>
      </Subpanel>

      <ProvenancePanel recordMeta={source.recordMeta} />
    </>
  );
}

function DetailSection({ hit, source, loading, onClose, onTrade }) {
  return (
    <section className="finder-detail-section" aria-label="Instrument detail">
      <header className="finder-detail-header">
        <div>
          <p className="muted finder-detail-eyebrow">
            {hit.scope.toUpperCase()} · {hit.document_id}
          </p>
          <h2>{hit.long_name}</h2>
          <p className="muted">{hit.asset_class || ""}</p>
        </div>
        <div className="finder-detail-actions">
          <button type="button" className="btn-primary" onClick={onTrade}>Place Order</button>
          <button type="button" className="btn-ghost" onClick={onClose}>Close</button>
        </div>
      </header>

      {loading && !source && <p className="muted">Loading document…</p>}
      {!loading && !source && <p className="muted">Document not available.</p>}

      {source && (
        <div className="subpanel-grid">
          {hit.scope === "fund" && <FundDetail source={source} />}
          {hit.scope === "equity" && <EquityDetail source={source} />}
          {hit.scope === "bond" && <BondDetail source={source} />}
        </div>
      )}
    </section>
  );
}

// ─── Quick order dialog (standalone, no portfolio context) ───────────────────

function QuickOrderDialog({ instrument, onClose }) {
  return (
    <OrderDialogBase
      isin={instrument.isin}
      instrumentName={instrument.name}
      currency={instrument.currency}
      suggestedPrice={instrument.price}
      portfolioId=""
      accountId=""
      onClose={onClose}
      title={`Place Order — ${instrument.shortName}`}
    />
  );
}

// ─── Order dialog (shared, used from custodian and instrument search) ─────────

export function OrderDialog({ isin, instrumentName, currency, suggestedPrice, positionQty, portfolioId, accountId, onClose }) {
  return (
    <OrderDialogBase
      isin={isin}
      instrumentName={instrumentName}
      currency={currency}
      suggestedPrice={suggestedPrice}
      positionQty={positionQty}
      portfolioId={portfolioId}
      accountId={accountId}
      onClose={onClose}
      title={`Trade — ${instrumentName}`}
    />
  );
}

function OrderDialogBase({ isin, instrumentName, currency, suggestedPrice, positionQty, portfolioId: initPortfolio, accountId: initAccount, onClose, title }) {
  const [side, setSide] = useState("buy");
  const [orderType, setOrderType] = useState("market");
  const [quantity, setQuantity] = useState("1");
  const [limitPrice, setLimitPrice] = useState(suggestedPrice != null ? String(suggestedPrice) : "");
  const [timeInForce, setTimeInForce] = useState("day");
  const [portfolioId, setPortfolioId] = useState(initPortfolio);
  const [accountId, setAccountId] = useState(initAccount);
  const [remarks, setRemarks] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [order, setOrder] = useState(null);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    return () => clearInterval(pollRef.current);
  }, []);

  useEffect(() => {
    if (order && !["filled", "cancelled", "rejected", "expired"].includes(order.status)) {
      pollRef.current = setInterval(async () => {
        try {
          const updated = await fetchOrder(order.orderId);
          setOrder(updated);
          if (["filled", "cancelled", "rejected", "expired"].includes(updated.status)) {
            clearInterval(pollRef.current);
          }
        } catch {
          clearInterval(pollRef.current);
        }
      }, 2000);
    }
    return () => clearInterval(pollRef.current);
  }, [order?.orderId, order?.status]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const payload = {
        portfolio_id: portfolioId || "STANDALONE",
        account_id: accountId || "STANDALONE",
        isin,
        instrument_name: instrumentName,
        side,
        order_type: orderType,
        quantity: parseFloat(quantity),
        currency,
        time_in_force: timeInForce,
        remarks,
      };
      if (suggestedPrice != null) {
        payload.reference_price = suggestedPrice;
      }
      if (orderType === "limit" || orderType === "stopLimit") {
        payload.limit_price = parseFloat(limitPrice);
      }
      const result = await submitOrder(payload);
      setOrder(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel() {
    if (!order) return;
    try {
      const updated = await cancelOrder(order.orderId);
      setOrder(updated);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-dialog order-dialog">
        <div className="modal-header">
          <h3>{title}</h3>
          <button type="button" className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="order-instr-row">
          <span className="mono order-isin">{isin}</span>
          <span className="order-ccy">{currency}</span>
          {suggestedPrice != null && (
            <span className="mono order-ref-price">Ref {fmtPrice(suggestedPrice, currency)}</span>
          )}
        </div>

        {!order ? (
          <form className="order-form" onSubmit={handleSubmit}>
            {(!initPortfolio) && (
              <div className="order-field-row">
                <label>Portfolio ID
                  <input value={portfolioId} onChange={(e) => setPortfolioId(e.target.value)}
                    placeholder="e.g. PF-001" />
                </label>
                <label>Account ID
                  <input value={accountId} onChange={(e) => setAccountId(e.target.value)}
                    placeholder="e.g. ACC-001" />
                </label>
              </div>
            )}

            <div className="order-side-row">
              {["buy", "sell"].map((s) => (
                <button
                  key={s}
                  type="button"
                  className={`order-side-btn ${s} ${side === s ? "active" : ""}`}
                  onClick={() => setSide(s)}
                >
                  {s.toUpperCase()}
                </button>
              ))}
            </div>

            <div className="order-field-row">
              <label>Order Type
                <select value={orderType} onChange={(e) => setOrderType(e.target.value)}>
                  <option value="market">Market</option>
                  <option value="limit">Limit</option>
                  <option value="stop">Stop</option>
                  <option value="stopLimit">Stop-Limit</option>
                </select>
              </label>
              <label>Time in Force
                <select value={timeInForce} onChange={(e) => setTimeInForce(e.target.value)}>
                  <option value="day">Day</option>
                  <option value="gtc">GTC</option>
                  <option value="ioc">IOC</option>
                  <option value="fok">FOK</option>
                </select>
              </label>
            </div>

            <div className="order-field-row">
              <label>Quantity
                <input
                  type="number"
                  min="1"
                  step="1"
                  max={side === "sell" && positionQty != null ? positionQty : undefined}
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  required
                />
              </label>
              {(orderType === "limit" || orderType === "stopLimit") && (
                <label>Limit Price ({currency})
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={limitPrice}
                    onChange={(e) => setLimitPrice(e.target.value)}
                    required
                  />
                </label>
              )}
            </div>

            <label className="order-remarks-label">Remarks
              <input
                type="text"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="Optional"
              />
            </label>

            {error && <p className="order-error">{error}</p>}

            <div className="order-actions">
              <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
              <button
                type="submit"
                className={`btn-primary order-submit ${side}`}
                disabled={submitting}
              >
                {submitting ? "Submitting…" : (() => {
                  const qty = parseFloat(quantity) || 0;
                  const price = parseFloat(limitPrice) || suggestedPrice || 0;
                  const total = qty * price;
                  const label = side === "buy" ? "Buy" : "Sell";
                  return total > 0
                    ? `${label} ${qty} · ${new Intl.NumberFormat("en-CH", { style: "currency", currency, maximumFractionDigits: 2 }).format(total)}`
                    : `${label} ${qty} ${currency}`;
                })()}
              </button>
            </div>
          </form>
        ) : (
          <OrderStatus order={order} onCancel={handleCancel} onClose={onClose} />
        )}
      </div>
    </div>
  );
}

// ─── Order status tracker ─────────────────────────────────────────────────────

function OrderStatus({ order, onCancel, onClose }) {
  const terminal = ["filled", "cancelled", "rejected", "expired"].includes(order.status);
  const statusMeta = ORDER_STATUS_META[order.status] ?? { label: order.status, cls: "" };

  return (
    <div className="order-status">
      <div className="order-status-header">
        <span className={`order-status-chip ${statusMeta.cls}`}>{statusMeta.label}</span>
        <span className="mono order-id">{order.orderId}</span>
      </div>

      <dl className="order-status-dl">
        <dt>Instrument</dt>
        <dd>{order.instrumentName}</dd>
        <dt>ISIN</dt>
        <dd className="mono">{order.isin}</dd>
        <dt>Side</dt>
        <dd className={`order-side-label ${order.side}`}>{order.side.toUpperCase()}</dd>
        <dt>Type</dt>
        <dd>{order.orderType}</dd>
        <dt>Quantity</dt>
        <dd className="mono">{order.quantity}</dd>
        {order.limitPrice != null && (
          <>
            <dt>Limit Price</dt>
            <dd className="mono">{order.limitPrice}</dd>
          </>
        )}
        <dt>Filled Qty</dt>
        <dd className="mono">{order.filledQuantity}</dd>
        {order.averageFillPrice != null && (
          <>
            <dt>Avg Fill Price</dt>
            <dd className="mono">{order.averageFillPrice.toFixed(4)}</dd>
          </>
        )}
        <dt>Submitted</dt>
        <dd className="mono">{new Date(order.submittedAt).toLocaleTimeString()}</dd>
      </dl>

      {order.fills.length > 0 && (
        <div className="order-fills">
          <h4>Fills</h4>
          <table className="order-fills-table">
            <thead>
              <tr><th>Fill ID</th><th className="r">Qty</th><th className="r">Price</th><th>Time</th></tr>
            </thead>
            <tbody>
              {order.fills.map((f) => (
                <tr key={f.fillId}>
                  <td className="mono">{f.fillId}</td>
                  <td className="r mono">{f.quantity}</td>
                  <td className="r mono">{f.price}</td>
                  <td className="mono">{new Date(f.filledAt).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!terminal && (
        <p className="order-polling-note">Waiting for fill…</p>
      )}

      <div className="order-actions">
        {!terminal && (
          <button type="button" className="btn-danger" onClick={onCancel}>Cancel Order</button>
        )}
        <button type="button" className="btn-ghost" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

// ─── Portfolio orders panel (embedded in custodian portfolio detail) ──────────

export function PortfolioOrdersPanel({ portfolioId }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const pollRef = useRef(null);

  const load = useCallback(() => {
    listPortfolioOrders(portfolioId)
      .then(setOrders)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [portfolioId]);

  useEffect(() => {
    load();
    pollRef.current = setInterval(load, 3000);
    return () => clearInterval(pollRef.current);
  }, [load]);

  if (loading) return <div className="instr-loading">Loading orders…</div>;
  if (!orders.length) return <p className="c-empty">No orders for this portfolio.</p>;

  return (
    <div className="table-wrap">
      <table className="order-list-table">
        <thead>
          <tr>
            <th>Order ID</th>
            <th>Instrument</th>
            <th>Side</th>
            <th>Type</th>
            <th className="r">Qty</th>
            <th className="r">Filled</th>
            <th className="r">Avg Price</th>
            <th>Status</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => {
            const meta = ORDER_STATUS_META[o.status] ?? { label: o.status, cls: "" };
            return (
              <tr key={o.orderId}>
                <td className="mono">{o.orderId}</td>
                <td>
                  <span className="instr-name">{o.instrumentName}</span>
                  <small className="mono"> {o.isin}</small>
                </td>
                <td><span className={`order-side-label ${o.side}`}>{o.side.toUpperCase()}</span></td>
                <td>{o.orderType}</td>
                <td className="r mono">{o.quantity}</td>
                <td className="r mono">{o.filledQuantity}</td>
                <td className="r mono">{o.averageFillPrice != null ? o.averageFillPrice.toFixed(4) : "—"}</td>
                <td><span className={`order-status-chip ${meta.cls}`}>{meta.label}</span></td>
                <td className="mono">{new Date(o.submittedAt).toLocaleTimeString()}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtPrice(price, currency) {
  if (price == null) return "—";
  return new Intl.NumberFormat("en-CH", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(price);
}

const TYPE_LABELS = {
  equity: "Equity",
  bond: "Bond",
  fund: "Fund",
  index: "Index",
  commodity: "Commodity",
  option: "Option",
  future: "Future",
  fxForward: "FX Forward",
  fxSwap: "FX Swap",
  fxOption: "FX Option",
  preciousMetal: "Precious Metal",
  realEstate: "Real Estate",
  cryptoAsset: "Crypto",
  alternative: "Alternative",
  cash: "Cash",
  other: "Other",
};

const ORDER_STATUS_META = {
  received: { label: "Received", cls: "status-pending" },
  validated: { label: "Validated", cls: "status-pending" },
  pending: { label: "Pending", cls: "status-pending" },
  partial: { label: "Partial", cls: "status-partial" },
  filled: { label: "Filled", cls: "status-filled" },
  cancelled: { label: "Cancelled", cls: "status-cancelled" },
  rejected: { label: "Rejected", cls: "status-rejected" },
  expired: { label: "Expired", cls: "status-cancelled" },
};
