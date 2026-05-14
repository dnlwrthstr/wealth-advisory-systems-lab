import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelOrder,
  listAllOrders,
  getOrderMode,
  setOrderMode,
  manualExecuteOrder,
} from "./services/api";

const STATUS_LABELS = {
  received: "Received",
  validated: "Validated",
  pending: "Pending",
  partial: "Partial",
  filled: "Filled",
  cancelled: "Cancelled",
  rejected: "Rejected",
  expired: "Expired",
};

const STATUS_CLASS = {
  received: "status-received",
  validated: "status-validated",
  pending: "status-pending",
  partial: "status-partial",
  filled: "status-filled",
  cancelled: "status-cancelled",
  rejected: "status-rejected",
  expired: "status-expired",
};

const TERMINAL = new Set(["filled", "cancelled", "rejected", "expired"]);
const PENDING_STATUSES = new Set(["received", "validated", "pending", "partial"]);

function fmtMoney(value, currency) {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-CH", {
    style: "currency",
    currency: currency || "CHF",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function fmtQty(value) {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-CH", { maximumFractionDigits: 4 }).format(value);
}

function fmtDate(iso) {
  if (!iso) return "—";
  return iso.slice(0, 16).replace("T", " ");
}

// ── Stats bar ────────────────────────────────────────────────────────────────

function StatsBar({ orders }) {
  const pending = orders.filter((o) => PENDING_STATUSES.has(o.status)).length;
  const filled = orders.filter((o) => o.status === "filled").length;
  const volume = orders
    .filter((o) => o.status === "filled")
    .reduce((sum, o) => {
      const gross = (o.averageFillPrice || 0) * (o.filledQuantity || 0);
      return sum + gross;
    }, 0);

  return (
    <div className="orders-stats">
      <span className="stat-chip stat-pending">Pending: {pending}</span>
      <span className="stat-chip stat-filled">Filled: {filled}</span>
      <span className="stat-chip stat-volume">
        Vol: {fmtMoney(volume, "CHF")}
      </span>
    </div>
  );
}

// ── Mode toggle ──────────────────────────────────────────────────────────────

function ModeToggle({ mode, onChange }) {
  const isAuto = mode === "auto";
  return (
    <div className="mode-toggle">
      <button
        type="button"
        className={`mode-btn ${isAuto ? "mode-active" : ""}`}
        onClick={() => onChange(true)}
      >
        Auto
      </button>
      <button
        type="button"
        className={`mode-btn ${!isAuto ? "mode-active" : ""}`}
        onClick={() => onChange(false)}
      >
        Manual
      </button>
    </div>
  );
}

// ── Order detail panel ────────────────────────────────────────────────────────

function OrderDetail({ order, onClose }) {
  if (!order) return null;
  return (
    <div className="order-detail-panel">
      <div className="order-detail-header">
        <h3>{order.orderId}</h3>
        <button type="button" className="btn-close" onClick={onClose}>✕</button>
      </div>
      <dl className="order-detail-grid">
        <div><dt>Instrument</dt><dd>{order.instrumentName}</dd></div>
        <div><dt>ISIN</dt><dd>{order.isin}</dd></div>
        <div><dt>Side</dt><dd className={`side-chip side-${order.side}`}>{order.side.toUpperCase()}</dd></div>
        <div><dt>Type</dt><dd>{order.orderType}</dd></div>
        <div><dt>Quantity</dt><dd>{fmtQty(order.quantity)}</dd></div>
        <div><dt>Currency</dt><dd>{order.currency}</dd></div>
        <div><dt>Limit price</dt><dd>{order.limitPrice != null ? fmtMoney(order.limitPrice, order.currency) : "—"}</dd></div>
        <div><dt>Status</dt><dd><span className={`order-status-chip ${STATUS_CLASS[order.status]}`}>{STATUS_LABELS[order.status]}</span></dd></div>
        <div><dt>Filled qty</dt><dd>{fmtQty(order.filledQuantity)}</dd></div>
        <div><dt>Avg fill price</dt><dd>{order.averageFillPrice != null ? fmtMoney(order.averageFillPrice, order.currency) : "—"}</dd></div>
        <div><dt>Submitted</dt><dd>{fmtDate(order.submittedAt)}</dd></div>
        <div><dt>Updated</dt><dd>{fmtDate(order.updatedAt)}</dd></div>
      </dl>

      {order.fills && order.fills.length > 0 && (
        <>
          <h4 style={{ marginTop: "1rem" }}>Fill History</h4>
          <table className="fills-table">
            <thead>
              <tr>
                <th>Fill ID</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Fee</th>
                <th>Net Amount</th>
                <th>Settlement</th>
                <th>P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {order.fills.map((f) => (
                <tr key={f.fillId}>
                  <td>{f.fillId}</td>
                  <td>{fmtQty(f.quantity)}</td>
                  <td>{fmtMoney(f.price, f.currency)}</td>
                  <td>{fmtMoney(f.fee, f.currency)}</td>
                  <td className={f.netAmount >= 0 ? "pnl-pos" : "pnl-neg"}>{fmtMoney(f.netAmount, f.currency)}</td>
                  <td>{f.settlementDate || "—"}</td>
                  <td className={f.realizedPnl == null ? "" : f.realizedPnl >= 0 ? "pnl-pos" : "pnl-neg"}>
                    {f.realizedPnl != null ? fmtMoney(f.realizedPnl, f.currency) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

// ── Orders table ─────────────────────────────────────────────────────────────

function OrdersTable({ orders, mode, onSelect, selectedId, onExecute, onCancel }) {
  return (
    <div className="orders-table-wrap">
      <table className="orders-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Instrument</th>
            <th>Side</th>
            <th>Qty</th>
            <th>Type</th>
            <th>Limit</th>
            <th>Currency</th>
            <th>Status</th>
            <th>Avg Fill</th>
            <th>Settlement</th>
            <th>Submitted</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {orders.length === 0 && (
            <tr>
              <td colSpan={12} style={{ textAlign: "center", color: "var(--muted)" }}>
                No orders
              </td>
            </tr>
          )}
          {orders.map((o) => {
            const isPending = PENDING_STATUSES.has(o.status);
            const settlementDate =
              o.fills && o.fills.length > 0 ? o.fills[o.fills.length - 1].settlementDate : null;
            return (
              <tr
                key={o.orderId}
                className={`order-row ${selectedId === o.orderId ? "order-row-selected" : ""}`}
                onClick={() => onSelect(o)}
              >
                <td className="order-id-cell">{o.orderId}</td>
                <td>
                  <div className="instrument-cell">
                    <span className="instrument-name">{o.instrumentName}</span>
                    <span className="instrument-isin">{o.isin}</span>
                  </div>
                </td>
                <td>
                  <span className={`side-chip side-${o.side}`}>{o.side.toUpperCase()}</span>
                </td>
                <td>{fmtQty(o.quantity)}</td>
                <td>{o.orderType}</td>
                <td>{o.limitPrice != null ? fmtMoney(o.limitPrice, o.currency) : "—"}</td>
                <td>{o.currency}</td>
                <td>
                  <span className={`order-status-chip ${STATUS_CLASS[o.status]} ${isPending && mode === "auto" ? "status-pulsing" : ""}`}>
                    {STATUS_LABELS[o.status]}
                  </span>
                </td>
                <td>{o.averageFillPrice != null ? fmtMoney(o.averageFillPrice, o.currency) : "—"}</td>
                <td>{settlementDate || "—"}</td>
                <td>{fmtDate(o.submittedAt)}</td>
                <td onClick={(e) => e.stopPropagation()}>
                  <div className="order-actions">
                    {isPending && mode === "manual" && (
                      <button
                        type="button"
                        className="btn-execute"
                        title="Execute"
                        onClick={() => onExecute(o.orderId)}
                      >
                        ⚡
                      </button>
                    )}
                    {isPending && (
                      <button
                        type="button"
                        className="btn-cancel-order"
                        title="Cancel"
                        onClick={() => onCancel(o.orderId)}
                      >
                        ✕
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Orders App ──────────────────────────────────────────────────────────

export default function OrdersApp() {
  const [orders, setOrders] = useState([]);
  const [mode, setMode] = useState("auto");
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterSide, setFilterSide] = useState("");
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  const loadOrders = useCallback(async () => {
    try {
      const data = await listAllOrders();
      setOrders(data);
      // refresh selected order details if open
      if (selectedOrder) {
        const updated = data.find((o) => o.orderId === selectedOrder.orderId);
        if (updated) setSelectedOrder(updated);
      }
    } catch (e) {
      setError(e.message);
    }
  }, [selectedOrder]);

  useEffect(() => {
    async function init() {
      try {
        const m = await getOrderMode();
        setMode(m.mode);
      } catch {}
      await loadOrders();
    }
    init();
  }, []);

  // Poll every 3s in auto mode, every 10s in manual
  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    const interval = mode === "auto" ? 3000 : 10000;
    pollRef.current = setInterval(loadOrders, interval);
    return () => clearInterval(pollRef.current);
  }, [mode, loadOrders]);

  async function handleModeChange(auto) {
    try {
      const res = await setOrderMode(auto);
      setMode(res.mode);
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleExecute(orderId) {
    try {
      await manualExecuteOrder(orderId);
      await loadOrders();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleCancel(orderId) {
    try {
      await cancelOrder(orderId);
      await loadOrders();
    } catch (e) {
      setError(e.message);
    }
  }

  const filtered = orders.filter((o) => {
    if (filterStatus && o.status !== filterStatus) return false;
    if (filterSide && o.side !== filterSide) return false;
    return true;
  });

  return (
    <section className="orders-layout">
      <div className="orders-toolbar">
        <div className="orders-toolbar-left">
          <ModeToggle mode={mode} onChange={handleModeChange} />
          <StatsBar orders={orders} />
        </div>
        <div className="orders-toolbar-right">
          <select
            className="filter-select"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="">All statuses</option>
            {Object.entries(STATUS_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
          <select
            className="filter-select"
            value={filterSide}
            onChange={(e) => setFilterSide(e.target.value)}
          >
            <option value="">Both sides</option>
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
          </select>
          <button
            type="button"
            className="btn-refresh"
            onClick={loadOrders}
            title="Refresh"
          >
            ↻
          </button>
        </div>
      </div>

      {error && <p className="orders-error">{error}</p>}

      <div className={`orders-content ${selectedOrder ? "orders-split" : ""}`}>
        <OrdersTable
          orders={filtered}
          mode={mode}
          onSelect={(o) => setSelectedOrder(o.orderId === selectedOrder?.orderId ? null : o)}
          selectedId={selectedOrder?.orderId}
          onExecute={handleExecute}
          onCancel={handleCancel}
        />
        {selectedOrder && (
          <OrderDetail
            order={selectedOrder}
            onClose={() => setSelectedOrder(null)}
          />
        )}
      </div>
    </section>
  );
}
