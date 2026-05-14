import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelOrder,
  fetchInstrumentTypes,
  fetchOrder,
  listPortfolioOrders,
  searchInstruments,
  submitOrder,
} from "./services/api";

// ─── Instrument search panel ────────────────────────────────────────────────

export default function InstrumentsApp() {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [currencyFilter, setCurrencyFilter] = useState("");
  const [types, setTypes] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [showOrder, setShowOrder] = useState(false);

  const debounceRef = useRef(null);

  useEffect(() => {
    fetchInstrumentTypes().then(setTypes).catch(() => {});
  }, []);

  const doSearch = useCallback(
    (q, type, currency) => {
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(async () => {
        setLoading(true);
        setError(null);
        try {
          const data = await searchInstruments({ q, type: type || null, currency: currency || null });
          setResults(data);
        } catch (err) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
      }, 300);
    },
    []
  );

  useEffect(() => {
    doSearch(query, typeFilter, currencyFilter);
  }, [query, typeFilter, currencyFilter, doSearch]);

  return (
    <div className="instr-layout">
      <div className="instr-search-col">
        <div className="instr-toolbar">
          <input
            className="instr-search-input"
            type="search"
            placeholder="Search by name, ISIN, or ticker…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select
            className="instr-filter-select"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="">All types</option>
            {types.map((t) => (
              <option key={t} value={t}>{TYPE_LABELS[t] ?? t}</option>
            ))}
          </select>
          <input
            className="instr-currency-input"
            type="text"
            placeholder="CCY"
            maxLength={3}
            value={currencyFilter}
            onChange={(e) => setCurrencyFilter(e.target.value.toUpperCase())}
          />
        </div>

        {error && <p className="instr-error">{error}</p>}

        <InstrumentTable
          results={results}
          loading={loading}
          selected={selected}
          onSelect={setSelected}
        />
      </div>

      <div className="instr-detail-col">
        {selected ? (
          <InstrumentDetail
            instrument={selected}
            onTrade={() => setShowOrder(true)}
          />
        ) : (
          <div className="instr-detail-empty">
            <p>Select an instrument to view details</p>
          </div>
        )}
      </div>

      {showOrder && selected && (
        <QuickOrderDialog
          instrument={selected}
          onClose={() => setShowOrder(false)}
        />
      )}
    </div>
  );
}

// ─── Instrument table ────────────────────────────────────────────────────────

function InstrumentTable({ results, loading, selected, onSelect }) {
  if (loading && !results) {
    return <div className="instr-loading">Searching…</div>;
  }

  const items = results?.items ?? [];
  const total = results?.total ?? 0;

  if (!loading && items.length === 0) {
    return <div className="instr-empty">No instruments found.</div>;
  }

  return (
    <div className="instr-table-wrap">
      {total > 0 && (
        <div className="instr-result-count">
          {total} instrument{total !== 1 ? "s" : ""}
          {loading && <span className="instr-refreshing"> · refreshing…</span>}
        </div>
      )}
      <table className="instr-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>ISIN</th>
            <th>Type</th>
            <th>CCY</th>
            <th className="r">Price</th>
            <th>Exchange</th>
          </tr>
        </thead>
        <tbody>
          {items.map((instr) => (
            <tr
              key={instr.id}
              className={selected?.id === instr.id ? "selected" : ""}
              onClick={() => onSelect(instr)}
            >
              <td>
                <span className="instr-name">{instr.name}</span>
                <small className="instr-ticker">{instr.shortName}</small>
              </td>
              <td><span className="mono">{instr.isin}</span></td>
              <td>
                <span className="instr-type-chip">{TYPE_LABELS[instr.type] ?? instr.type}</span>
              </td>
              <td><span className="mono">{instr.currency}</span></td>
              <td className="r mono">{fmtPrice(instr.price, instr.currency)}</td>
              <td>{instr.exchange ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Instrument detail panel ─────────────────────────────────────────────────

function InstrumentDetail({ instrument: i, onTrade }) {
  return (
    <div className="instr-detail">
      <div className="instr-detail-header">
        <div>
          <h2 className="instr-detail-name">{i.name}</h2>
          <p className="instr-detail-sub">
            <span className="instr-type-chip">{TYPE_LABELS[i.type] ?? i.type}</span>
            {i.exchange && <span className="instr-tag">{i.exchange}</span>}
            {i.country && <span className="instr-tag">{i.country}</span>}
          </p>
        </div>
        <button type="button" className="btn-primary" onClick={onTrade}>
          Place Order
        </button>
      </div>

      <dl className="instr-dl">
        <dt>ISIN</dt>
        <dd className="mono">{i.isin}</dd>
        <dt>Ticker</dt>
        <dd className="mono">{i.shortName}</dd>
        <dt>Currency</dt>
        <dd className="mono">{i.currency}</dd>
        <dt>Price</dt>
        <dd className="mono">{fmtPrice(i.price, i.currency)}</dd>
        {i.sector && (
          <>
            <dt>Sector</dt>
            <dd>{i.sector.replace(/_/g, " ")}</dd>
          </>
        )}
        {i.couponPct != null && (
          <>
            <dt>Coupon</dt>
            <dd className="mono">{i.couponPct.toFixed(3)} %</dd>
          </>
        )}
        {i.maturityDate && (
          <>
            <dt>Maturity</dt>
            <dd className="mono">{i.maturityDate}</dd>
          </>
        )}
        {i.yieldPct != null && (
          <>
            <dt>Yield</dt>
            <dd className="mono">{i.yieldPct.toFixed(3)} %</dd>
          </>
        )}
      </dl>

      {i.description && <p className="instr-desc">{i.description}</p>}
    </div>
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

export function OrderDialog({ isin, instrumentName, currency, suggestedPrice, portfolioId, accountId, onClose }) {
  return (
    <OrderDialogBase
      isin={isin}
      instrumentName={instrumentName}
      currency={currency}
      suggestedPrice={suggestedPrice}
      portfolioId={portfolioId}
      accountId={accountId}
      onClose={onClose}
      title={`Trade — ${instrumentName}`}
    />
  );
}

function OrderDialogBase({ isin, instrumentName, currency, suggestedPrice, portfolioId: initPortfolio, accountId: initAccount, onClose, title }) {
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
                  min="0.01"
                  step="1"
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
                {submitting ? "Submitting…" : `${side === "buy" ? "Buy" : "Sell"} ${quantity} ${currency}`}
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
