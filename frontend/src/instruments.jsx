import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelOrder,
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
  const [issuer, setIssuer] = useState("");
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
      issuer,
      type: typeTab,
      currency: currencyFilter || null,
      country: countryFilter || null,
    });
  }, [identifier, name, issuer, typeTab, currencyFilter, countryFilter, doSearch]);

  const items = results?.items ?? [];
  const total = results?.total ?? 0;
  const selected = items.find((h) => h.document_id === selectedId) || null;

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

        <div className="finder-fields">
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
          <label className="finder-field">
            <span className="finder-field-label">Issuer</span>
            <span className="finder-input-wrap">
              <span className="finder-input-icon">⌂</span>
              <input
                type="search"
                value={issuer}
                placeholder="Issuer legal name"
                onChange={(e) => setIssuer(e.target.value)}
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
            {loading ? "Searching…" : `${total} result${total === 1 ? "" : "s"}`}
          </span>
          <span className="finder-index-name">Index: pms_golden_instrumentsearch</span>
        </div>

        {!loading && items.length === 0 && (
          <p className="finder-empty">No instruments matched.</p>
        )}

        <ul className="finder-list">
          {items.map((hit) => (
            <ResultCard
              key={`${hit.scope}:${hit.document_id}`}
              hit={hit}
              selected={selectedId === hit.document_id}
              onSelect={() => setSelectedId(hit.document_id)}
            />
          ))}
        </ul>
      </section>

      {selected && (
        <DetailPanel
          hit={selected}
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

// ─── Result card ────────────────────────────────────────────────────────────

function ResultCard({ hit, selected, onSelect }) {
  const isin =
    (hit.identifiers || []).find((id) => (id.type || "").toLowerCase() === "isin")?.identifier
    || "";
  const ticker = hit.ticker || hit.short_name || "";
  const quality = hit.quality_score != null ? `${Math.round(hit.quality_score * 100)}%` : null;
  const subtitle = hit.short_name || hit.issuer_legal_name || "";

  return (
    <li>
      <button
        type="button"
        className={`finder-card${selected ? " selected" : ""}`}
        onClick={onSelect}
      >
        <aside className="finder-card-ident">
          <strong className="finder-card-ident-name">{hit.long_name}</strong>
          <span className="finder-card-ident-isin mono">{isin || hit.document_id}</span>
          <span className="finder-card-ident-tag">{labelForType(hit.ow_type)}</span>
          {ticker && <span className="finder-card-ident-ticker mono">{ticker}</span>}
        </aside>
        <div className="finder-card-main">
          <div className="finder-card-head">
            <span className="finder-card-class">{hit.asset_class || ""}</span>
            <span className="finder-card-status">{hit.lifecycle_status || "active"}</span>
            {quality && <span className="finder-card-quality">Quality {quality}</span>}
          </div>
          <h3 className="finder-card-title">{hit.long_name}</h3>
          {subtitle && <p className="finder-card-sub">{subtitle}</p>}
          {hit.issuer_legal_name && hit.scope === "fund" && (
            <p className="finder-card-sub">Umbrella: {hit.issuer_legal_name}</p>
          )}
          <div className="finder-card-tags">
            <span className="finder-tag finder-tag-id mono">{hit.document_id}</span>
            {hit.ow_type && <span className="finder-tag">{labelForType(hit.ow_type).toLowerCase()}</span>}
            {hit.country && <span className="finder-tag">{hit.country}</span>}
            {hit.currency && <span className="finder-tag">{hit.currency}</span>}
            {hit.cfi_code && <span className="finder-tag mono">CFI {hit.cfi_code}</span>}
          </div>
        </div>
      </button>
    </li>
  );
}

function labelForType(t) {
  return ({ equity: "EQUITY", simpleBond: "BOND", fund: "FUND" })[t] || t.toUpperCase();
}

// ─── Detail panel (overlay) ─────────────────────────────────────────────────

function DetailPanel({ hit, onClose, onTrade }) {
  return (
    <aside className="finder-detail" aria-label="Instrument detail">
      <div className="finder-detail-head">
        <div>
          <h3>{hit.long_name}</h3>
          <p className="muted">{hit.asset_class}</p>
        </div>
        <div className="finder-detail-actions">
          <button type="button" className="btn-primary" onClick={onTrade}>Place Order</button>
          <button type="button" className="btn-ghost" onClick={onClose}>Close</button>
        </div>
      </div>
      <dl className="finder-dl">
        <dt>Document</dt><dd className="mono">{hit.scope}/{hit.document_id}</dd>
        {hit.cfi_code && (<><dt>CFI</dt><dd className="mono">{hit.cfi_code}</dd></>)}
        {hit.currency && (<><dt>Currency</dt><dd className="mono">{hit.currency}</dd></>)}
        {hit.country && (<><dt>Country</dt><dd className="mono">{hit.country}</dd></>)}
        {hit.venue_mic && (<><dt>Primary venue</dt><dd className="mono">{hit.venue_mic}</dd></>)}
        {hit.ticker && (<><dt>Ticker</dt><dd className="mono">{hit.ticker}</dd></>)}
        {hit.issuer_legal_name && (<><dt>Issuer</dt><dd>{hit.issuer_legal_name}</dd></>)}
        {hit.issuer_lei && (<><dt>Issuer LEI</dt><dd className="mono">{hit.issuer_lei}</dd></>)}
        {hit.management_company_name && (<><dt>Management Co.</dt><dd>{hit.management_company_name}</dd></>)}
        {hit.promoter_name && (<><dt>Promoter</dt><dd>{hit.promoter_name}</dd></>)}
        {hit.lifecycle_status && (<><dt>Lifecycle</dt><dd>{hit.lifecycle_status}</dd></>)}
      </dl>
      {(hit.identifiers || []).length > 0 && (
        <section>
          <h4>Identifiers</h4>
          <ul className="finder-id-list">
            {(hit.identifiers || []).map((id) => (
              <li key={`${id.type}:${id.identifier}`}>
                <span className="finder-tag">{(id.type || "").toUpperCase()}</span>
                <span className="mono">{id.identifier}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </aside>
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
