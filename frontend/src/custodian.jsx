import React, { useEffect, useMemo, useState } from "react";
import { fetchCustodySnapshot, listCustodyCustomers } from "./services/api";

// ---------------------------------------------------------------------------
// Label maps
// ---------------------------------------------------------------------------

const ASSET_CLASS_META = {
  cash:        { label: "Cash & Liquidity",  color: "#64736c" },
  bond:        { label: "Fixed Income",      color: "#2563eb" },
  equity:      { label: "Equities",          color: "#16a34a" },
  fund:        { label: "Funds & ETFs",      color: "#9333ea" },
  commodity:   { label: "Commodities",       color: "#d97706" },
  realEstate:  { label: "Real Estate",       color: "#0891b2" },
  alternative: { label: "Alternatives",      color: "#dc2626" },
  cryptoAsset: { label: "Digital Assets",    color: "#f59e0b" },
  index:       { label: "Indices",           color: "#6366f1" },
  other:       { label: "Other",             color: "#6b7280" },
};
const ASSET_CLASS_ORDER = [
  "cash", "bond", "equity", "fund", "commodity",
  "realEstate", "alternative", "cryptoAsset", "index", "other",
];

const TX_LABELS = {
  buy: "Buy", sell: "Sell", buyToClose: "Buy to Close", sellToOpen: "Sell to Open",
  inflowCash: "Cash In", outflowCash: "Cash Out", internalTransfer: "Transfer",
  dividendCash: "Dividend", dividendReinvestment: "Reinvest", dividendStock: "Stock Div",
  dividendChoice: "Div. Choice", coupon: "Coupon", interestPayment: "Interest",
  fees: "Fees", taxes: "Taxes", taxCorrections: "Tax Adj", managementFee: "Mgmt Fee",
  custodyFee: "Custody Fee", subscription: "Subscribe", redemption: "Redeem",
  redemptionPartial: "Part. Redeem", fxSpot: "FX Spot", merger: "Merger",
  stockSplit: "Stock Split", spinOff: "Spin-off", bonus: "Bonus",
  capitalIncrease: "Cap. Increase", other: "Other",
};

const MVT_LABELS = {
  interest: "Interest", brokerageFee: "Brokerage", commission: "Commission",
  withholdingTax: "WHT", capitalGainTax: "CGT", financialTransactionTax: "FTT",
  managementFee: "Mgmt Fee", custodyFee: "Custody", accruedInterest: "Accrued",
  otherFee: "Fee", otherTax: "Tax", stampDuty: "Stamp Duty", premium: "Premium",
  reclaimableTax: "Reclaim Tax", valueAddedTax: "VAT",
};

const SEGMENT_LABELS = {
  retail: "Retail", privateClient: "Private Client", highNetWorth: "High Net Worth",
  ultraHighNetWorth: "Ultra HNW", familyOffice: "Family Office",
  institutional: "Institutional", corporate: "Corporate",
};

const STRATEGY_LABELS = {
  capitalPreservation: "Capital Preservation", income: "Income",
  balanced: "Balanced", balancedGrowth: "Balanced Growth",
  capitalGrowth: "Capital Growth", aggressiveGrowth: "Aggressive Growth",
};

const MANDATE_LABELS = {
  discretionary: "Discretionary", advisory: "Advisory", executionOnly: "Execution Only",
};

// ---------------------------------------------------------------------------
// Formatters
// ---------------------------------------------------------------------------

function fmtCcy(value, currency) {
  if (value == null) return "—";
  return new Intl.NumberFormat("de-CH", {
    style: "currency", currency: currency ?? "CHF", maximumFractionDigits: 0,
  }).format(value);
}

function fmtNum(value, decimals = 2) {
  if (value == null) return "—";
  return new Intl.NumberFormat("de-CH", {
    minimumFractionDigits: decimals, maximumFractionDigits: decimals,
  }).format(value);
}

function fmtDate(dateStr) {
  if (!dateStr) return "—";
  const parts = String(dateStr).split("T")[0].split("-");
  if (parts.length !== 3) return dateStr;
  return `${parts[2]}.${parts[1]}.${parts[0]}`;
}

function fmtPct(weight) {
  if (weight == null) return "—";
  return `${(weight * 100).toFixed(1)} %`;
}

function fmtLabel(map, key) {
  return map[key] ?? key;
}

// ---------------------------------------------------------------------------
// Movement summary — compact one-liner for transaction rows
// ---------------------------------------------------------------------------

function movementSummary(movements) {
  if (!movements?.length) return null;
  const parts = [];

  // Asset legs
  for (const m of movements) {
    if (m.type === "asset" && m.quantity) {
      const sign = m.quantity.value >= 0 ? "+" : "";
      const shortName = m.financialInstrument?.name?.split(" ").slice(0, 4).join(" ") ?? "";
      parts.push(`${sign}${fmtNum(Math.abs(m.quantity.value), 0)} ${m.quantity.unit === "nominal" ? "nom." : "u."} ${shortName}`);
    }
  }

  // Cash legs (net)
  const cashLegs = movements.filter((m) => m.type === "cash" && m.amount != null);
  if (cashLegs.length) {
    const byCcy = {};
    for (const leg of cashLegs) {
      const k = leg.currency ?? "CHF";
      byCcy[k] = (byCcy[k] ?? 0) + leg.amount;
    }
    for (const [ccy, total] of Object.entries(byCcy)) {
      parts.push(fmtCcy(total, ccy));
    }
  }

  // Fee / tax legs
  const feeLegs = movements.filter((m) => MVT_LABELS[m.type] && m.amount != null);
  for (const m of feeLegs) {
    parts.push(`${MVT_LABELS[m.type]} ${fmtCcy(m.amount, m.currency)}`);
  }

  return parts.join("  ·  ");
}

// ---------------------------------------------------------------------------
// TX type chip styling
// ---------------------------------------------------------------------------

function txChipClass(type) {
  if (["buy", "subscription", "inflowCash"].includes(type)) return "tx-chip buy";
  if (["sell", "redemption", "redemptionPartial", "outflowCash"].includes(type)) return "tx-chip sell";
  if (["dividendCash", "dividendReinvestment", "coupon", "interestPayment", "bonus"].includes(type)) return "tx-chip income";
  if (["fees", "taxes", "taxCorrections", "managementFee", "custodyFee"].includes(type)) return "tx-chip fee";
  return "tx-chip neutral";
}

// ---------------------------------------------------------------------------
// Shared: KPI card
// ---------------------------------------------------------------------------

function Kpi({ label, value }) {
  return (
    <div className="kpi-card">
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Breadcrumb
// ---------------------------------------------------------------------------

function Breadcrumb({ crumbs }) {
  return (
    <nav className="c-breadcrumb">
      {crumbs.map((crumb, i) => (
        <React.Fragment key={i}>
          {i > 0 && <span className="c-breadcrumb-sep">›</span>}
          {crumb.onClick ? (
            <button type="button" className="c-breadcrumb-link" onClick={crumb.onClick}>
              {crumb.label}
            </button>
          ) : (
            <span className="c-breadcrumb-current">{crumb.label}</span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}

// ---------------------------------------------------------------------------
// VIEW 1 — Customer search / list
// ---------------------------------------------------------------------------

function CustomerList({ customers, search, onSearch, onSelect, loading, error }) {
  if (loading) {
    return <div className="c-loading">Loading customers…</div>;
  }
  if (error) {
    return <div className="c-error">Could not load customers: {error}</div>;
  }

  return (
    <div className="c-view">
      <div className="c-list-header">
        <h2>Customers</h2>
        <input
          className="c-search"
          type="search"
          placeholder="Search by name, ID, segment…"
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          autoFocus
        />
      </div>

      <p className="c-count">{customers.length} client{customers.length !== 1 ? "s" : ""}</p>

      <div className="c-customer-grid">
        {customers.map((c) => (
          <button
            key={c.id}
            type="button"
            className="c-customer-card"
            onClick={() => onSelect(c.id)}
          >
            <div className="c-customer-main">
              <strong>{c.name}</strong>
              <span className="c-segment-badge">{fmtLabel(SEGMENT_LABELS, c.customerSegment)}</span>
            </div>
            <div className="c-customer-meta">
              <span>{c.id}</span>
              <span>{c.referenceCurrency}</span>
              {c.bankAdvisor && <span>RM: {c.bankAdvisor}</span>}
            </div>
            <span className="c-chevron">›</span>
          </button>
        ))}
        {customers.length === 0 && (
          <p className="c-empty">No customers match your search.</p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// VIEW 2 — Customer overview + portfolio selection
// ---------------------------------------------------------------------------

function CustomerOverview({ snapshot, loading, onSelectPortfolio, onBack }) {
  if (loading) {
    return <div className="c-loading">Loading portfolio data…</div>;
  }
  if (!snapshot) return null;

  const { customer, portfolios, accounts, positions, transactions, totalMarketValue, baseCurrency, assetAllocation } = snapshot;

  // Deduplicate portfolios (snapshot may list a portfolio once per account)
  const uniquePortfolios = portfolios.reduce((acc, pf) => {
    if (!acc.some((p) => p.identification === pf.identification)) acc.push(pf);
    return acc;
  }, []);

  // Compute per-portfolio AUM
  const portfolioAum = {};
  for (const pf of uniquePortfolios) {
    const pfAccountIds = new Set(
      accounts
        .filter((a) => a.portfolioInformation?.identification === pf.identification)
        .map((a) => a.id)
    );
    const pfPositions = positions.filter((p) => pfAccountIds.has(p.account.id));
    portfolioAum[pf.identification] = pfPositions.reduce(
      (sum, p) => sum + (p.valuation.baseValue ?? p.valuation.totalValue), 0
    );
  }

  return (
    <div className="c-view">
      <Breadcrumb
        crumbs={[
          { label: "Customers", onClick: onBack },
          { label: customer.name },
        ]}
      />

      {/* Customer header */}
      <div className="c-customer-header">
        <div>
          <h2>{customer.name}</h2>
          <p className="c-customer-subtitle">
            {fmtLabel(SEGMENT_LABELS, customer.customerSegment)}
            {customer.bankAdvisor && <> · RM: {customer.bankAdvisor}</>}
            {customer.language && <> · {customer.language.toUpperCase()}</>}
          </p>
        </div>
        <div className="c-kpi-row">
          <Kpi label="Total AUM" value={fmtCcy(totalMarketValue, baseCurrency)} />
          <Kpi label="Portfolios" value={uniquePortfolios.length} />
          <Kpi label="Positions" value={positions.length} />
          <Kpi label="Transactions" value={transactions.length} />
        </div>
      </div>

      {/* Asset allocation bar */}
      <div className="c-section">
        <h3>Asset Allocation</h3>
        <div className="c-allocation-bars">
          {assetAllocation.map((item) => {
            const meta = ASSET_CLASS_META[item.instrumentType] ?? ASSET_CLASS_META.other;
            return (
              <div key={item.label} className="c-alloc-row">
                <span className="c-alloc-label">{meta.label}</span>
                <div className="c-alloc-track">
                  <div
                    className="c-alloc-fill"
                    style={{ width: `${Math.max(item.weight * 100, 0.5)}%`, background: meta.color }}
                  />
                </div>
                <span className="c-alloc-pct">{fmtPct(item.weight)}</span>
                <span className="c-alloc-val">{fmtCcy(item.marketValue, baseCurrency)}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Portfolio cards */}
      <div className="c-section">
        <h3>Portfolios</h3>
        <div className="c-portfolio-grid">
          {uniquePortfolios.map((pf) => {
            const aum = portfolioAum[pf.identification] ?? 0;
            const share = totalMarketValue > 0 ? aum / totalMarketValue : 0;
            const pfAccounts = accounts.filter(
              (a) => a.portfolioInformation?.identification === pf.identification
            );
            const pfPositionCount = positions.filter((p) =>
              pfAccounts.some((a) => a.id === p.account.id)
            ).length;

            return (
              <button
                key={pf.identification}
                type="button"
                className="c-portfolio-card"
                onClick={() => onSelectPortfolio(pf.identification)}
              >
                <div className="c-portfolio-top">
                  <strong>{pf.name ?? pf.identification}</strong>
                  <span className="c-mandate-badge">
                    {fmtLabel(MANDATE_LABELS, pf.mandateType)}
                  </span>
                </div>
                <div className="c-portfolio-strategy">
                  {fmtLabel(STRATEGY_LABELS, pf.strategy)}
                </div>
                <div className="c-portfolio-bottom">
                  <div className="c-portfolio-kpis">
                    <span>{fmtCcy(aum, baseCurrency)}</span>
                    <span>{fmtPct(share)} of AUM</span>
                    <span>{pfPositionCount} positions</span>
                    <span>{pfAccounts.length} account{pfAccounts.length !== 1 ? "s" : ""}</span>
                  </div>
                  <span className="c-chevron">›</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// VIEW 3 — Portfolio detail: positions by asset class + transactions
// ---------------------------------------------------------------------------

function PortfolioDetail({ snapshot, portfolioId, onBack, onBackToCustomer }) {
  const { customer, accounts, positions, transactions, baseCurrency } = snapshot;

  const portfolioInfo = snapshot.portfolios.find((p) => p.identification === portfolioId);
  const portfolioAccounts = accounts.filter(
    (a) => a.portfolioInformation?.identification === portfolioId
  );
  const portfolioAccountIds = new Set(portfolioAccounts.map((a) => a.id));
  const pfPositions = positions.filter((p) => portfolioAccountIds.has(p.account.id));

  const totalBase = pfPositions.reduce(
    (sum, p) => sum + (p.valuation.baseValue ?? p.valuation.totalValue), 0
  );

  const positionDate = pfPositions[0]?.positionDate;

  // Group positions by asset class
  const grouped = {};
  for (const pos of pfPositions) {
    const type = pos.financialInstrument.type;
    const key = ASSET_CLASS_META[type] ? type : "other";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(pos);
  }

  return (
    <div className="c-view">
      <Breadcrumb
        crumbs={[
          { label: "Customers", onClick: onBack },
          { label: customer.name, onClick: onBackToCustomer },
          { label: portfolioInfo?.name ?? portfolioId },
        ]}
      />

      {/* Portfolio header */}
      <div className="c-portfolio-header">
        <div>
          <h2>{portfolioInfo?.name ?? portfolioId}</h2>
          <p className="c-customer-subtitle">
            {fmtLabel(STRATEGY_LABELS, portfolioInfo?.strategy)}
            {" · "}
            {fmtLabel(MANDATE_LABELS, portfolioInfo?.mandateType)}
            {" · "}
            {baseCurrency}
          </p>
        </div>
        <div className="c-kpi-row">
          <Kpi label="AUM" value={fmtCcy(totalBase, baseCurrency)} />
          <Kpi label="Positions" value={pfPositions.length} />
          <Kpi label="Accounts" value={portfolioAccounts.length} />
          {positionDate && <Kpi label="As of" value={fmtDate(positionDate)} />}
        </div>
      </div>

      {/* Positions by asset class */}
      <div className="c-section">
        <h3>Positions</h3>
        {ASSET_CLASS_ORDER.filter((ac) => grouped[ac]?.length > 0).map((ac) => (
          <AssetClassSection
            key={ac}
            assetClass={ac}
            positions={grouped[ac]}
            baseCurrency={baseCurrency}
            portfolioTotal={totalBase}
          />
        ))}
        {pfPositions.length === 0 && (
          <p className="c-empty">No positions for this portfolio.</p>
        )}
      </div>

      {/* Transactions */}
      <div className="c-section">
        <h3>Transactions</h3>
        <TransactionList transactions={transactions} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Positions section for one asset class
// ---------------------------------------------------------------------------

function AssetClassSection({ assetClass, positions, baseCurrency, portfolioTotal }) {
  const [collapsed, setCollapsed] = useState(false);
  const meta = ASSET_CLASS_META[assetClass];
  const sectionTotal = positions.reduce(
    (sum, p) => sum + (p.valuation.baseValue ?? p.valuation.totalValue), 0
  );
  const sectionWeight = portfolioTotal > 0 ? sectionTotal / portfolioTotal : 0;

  const isCash = assetClass === "cash";
  const isBond = assetClass === "bond";

  return (
    <div className="c-asset-section">
      <button
        type="button"
        className="c-asset-header"
        onClick={() => setCollapsed((v) => !v)}
        style={{ "--ac-color": meta.color }}
      >
        <span className="c-asset-dot" />
        <span className="c-asset-name">{meta.label}</span>
        <span className="c-asset-count">{positions.length}</span>
        <span className="c-asset-total">{fmtCcy(sectionTotal, baseCurrency)}</span>
        <span className="c-asset-pct">{fmtPct(sectionWeight)}</span>
        <span className="c-collapse-icon">{collapsed ? "▶" : "▼"}</span>
      </button>

      {!collapsed && (
        <div className="table-wrap">
          <table className="c-pos-table">
            {isCash && <CashHeader />}
            {isBond && <BondHeader baseCurrency={baseCurrency} />}
            {!isCash && !isBond && <SecurityHeader baseCurrency={baseCurrency} />}
            <tbody>
              {positions.map((pos) => (
                isCash
                  ? <CashRow key={pos.id} pos={pos} />
                  : isBond
                  ? <BondRow key={pos.id} pos={pos} baseCurrency={baseCurrency} />
                  : <SecurityRow key={pos.id} pos={pos} baseCurrency={baseCurrency} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Cash columns
function CashHeader() {
  return (
    <thead>
      <tr>
        <th>Name</th>
        <th className="r">Currency</th>
        <th className="r">Balance</th>
        <th>Safekeeping</th>
      </tr>
    </thead>
  );
}
function CashRow({ pos }) {
  return (
    <tr>
      <td>{pos.financialInstrument.name}</td>
      <td className="r mono">{pos.currency}</td>
      <td className="r mono">{fmtCcy(pos.valuation.totalValue, pos.currency)}</td>
      <td>{pos.safekeepingPlace ?? "—"}</td>
    </tr>
  );
}

// Bond columns — nominal, dirty price %, accrued interest
function BondHeader({ baseCurrency }) {
  return (
    <thead>
      <tr>
        <th>Name</th>
        <th>ISIN</th>
        <th className="r">Nominal</th>
        <th className="r">Price %</th>
        <th className="r">Accrued</th>
        <th className="r">Mkt Value</th>
        <th className="r">Base ({baseCurrency})</th>
        <th className="r">Weight</th>
      </tr>
    </thead>
  );
}
function BondRow({ pos, baseCurrency }) {
  const fi = pos.financialInstrument;
  return (
    <tr>
      <td>
        <span className="c-instr-name">{fi.name}</span>
        {fi.country && <small className="c-tag">{fi.country}</small>}
      </td>
      <td><span className="mono">{fi.isin ?? "—"}</span></td>
      <td className="r mono">{fmtNum(pos.quantity.value, 0)}</td>
      <td className="r mono">{pos.price ? fmtNum(pos.price.value, 3) : "—"}</td>
      <td className="r mono">
        {pos.accruedInterest
          ? fmtCcy(pos.accruedInterest.value, pos.accruedInterest.currency)
          : "—"}
      </td>
      <td className="r mono">{fmtCcy(pos.valuation.totalValue, pos.valuation.currency)}</td>
      <td className="r mono">
        {pos.valuation.baseValue != null
          ? fmtCcy(pos.valuation.baseValue, baseCurrency)
          : fmtCcy(pos.valuation.totalValue, baseCurrency)}
      </td>
      <td className="r mono">{fmtPct(pos.weight)}</td>
    </tr>
  );
}

// Equity / Fund / Other columns
function SecurityHeader({ baseCurrency }) {
  return (
    <thead>
      <tr>
        <th>Name</th>
        <th>ISIN</th>
        <th className="r">Qty</th>
        <th className="r">Price</th>
        <th>CCY</th>
        <th className="r">Mkt Value</th>
        <th className="r">Base ({baseCurrency})</th>
        <th className="r">Weight</th>
      </tr>
    </thead>
  );
}
function SecurityRow({ pos, baseCurrency }) {
  const fi = pos.financialInstrument;
  return (
    <tr>
      <td>
        <span className="c-instr-name">{fi.name}</span>
        {fi.sector && <small className="c-tag">{fi.sector.replace(/_/g, " ")}</small>}
      </td>
      <td><span className="mono">{fi.isin ?? "—"}</span></td>
      <td className="r mono">{fmtNum(pos.quantity.value, pos.quantity.unit === "nominal" ? 0 : 2)}</td>
      <td className="r mono">
        {pos.price ? fmtNum(pos.price.value, pos.price.currency === "CHF" ? 2 : 2) : "—"}
      </td>
      <td><span className="mono">{fi.currency}</span></td>
      <td className="r mono">{fmtCcy(pos.valuation.totalValue, pos.valuation.currency)}</td>
      <td className="r mono">
        {pos.valuation.baseValue != null
          ? fmtCcy(pos.valuation.baseValue, baseCurrency)
          : fmtCcy(pos.valuation.totalValue, baseCurrency)}
      </td>
      <td className="r mono">{fmtPct(pos.weight)}</td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Transaction list
// ---------------------------------------------------------------------------

function TransactionList({ transactions }) {
  const sorted = [...transactions].sort(
    (a, b) => b.transactionDate.localeCompare(a.transactionDate)
  );

  if (!sorted.length) {
    return <p className="c-empty">No transactions.</p>;
  }

  return (
    <div className="table-wrap">
      <table className="c-tx-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Type</th>
            <th>Description</th>
            <th>Movements</th>
            <th>Value Date</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((tx) => {
            const summary = movementSummary(tx.movementList);
            return (
              <tr key={tx.id}>
                <td className="mono">{fmtDate(tx.transactionDate)}</td>
                <td>
                  <span className={txChipClass(tx.type)}>
                    {fmtLabel(TX_LABELS, tx.type)}
                  </span>
                </td>
                <td className="c-tx-desc">{tx.description}</td>
                <td className="c-tx-movements mono">{summary ?? "—"}</td>
                <td className="mono">{fmtDate(tx.valueDate)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main exported component
// ---------------------------------------------------------------------------

export default function CustodianApp() {
  const [customers, setCustomers] = useState([]);
  const [search, setSearch] = useState("");
  const [loadingCustomers, setLoadingCustomers] = useState(true);
  const [customersError, setCustomersError] = useState(null);

  const [snapshot, setSnapshot] = useState(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [selectedCustomerId, setSelectedCustomerId] = useState(null);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState(null);
  const [view, setView] = useState("list"); // 'list' | 'customer' | 'portfolio'

  useEffect(() => {
    listCustodyCustomers()
      .then(setCustomers)
      .catch((err) => setCustomersError(err.message))
      .finally(() => setLoadingCustomers(false));
  }, []);

  async function selectCustomer(customerId) {
    setSelectedCustomerId(customerId);
    setSelectedPortfolioId(null);
    setView("customer");
    setSnapshotLoading(true);
    setSnapshot(null);
    try {
      setSnapshot(await fetchCustodySnapshot(customerId));
    } catch (err) {
      setCustomersError(err.message);
    } finally {
      setSnapshotLoading(false);
    }
  }

  const filteredCustomers = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return customers;
    return customers.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.id.toLowerCase().includes(q) ||
        (c.customerSegment ?? "").toLowerCase().includes(q) ||
        (c.bankAdvisor ?? "").toLowerCase().includes(q)
    );
  }, [customers, search]);

  if (view === "list") {
    return (
      <CustomerList
        customers={filteredCustomers}
        search={search}
        onSearch={setSearch}
        onSelect={selectCustomer}
        loading={loadingCustomers}
        error={customersError}
      />
    );
  }

  if (view === "customer") {
    return (
      <CustomerOverview
        snapshot={snapshot}
        loading={snapshotLoading}
        onSelectPortfolio={(pfId) => {
          setSelectedPortfolioId(pfId);
          setView("portfolio");
        }}
        onBack={() => setView("list")}
      />
    );
  }

  if (view === "portfolio" && snapshot && selectedPortfolioId) {
    return (
      <PortfolioDetail
        snapshot={snapshot}
        portfolioId={selectedPortfolioId}
        onBack={() => setView("list")}
        onBackToCustomer={() => setView("customer")}
      />
    );
  }

  return null;
}
