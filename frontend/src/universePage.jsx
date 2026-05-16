import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  addToUniverse,
  assembleInstrument,
  fetchUniverse,
  updateUniverseStatus,
} from "./services/api";

// Shared base for the per-type Universe pages. The three wrapper
// components (universeEquity.jsx, universeBond.jsx, universeFund.jsx)
// supply scope plus a `columns` spec describing the per-type list
// columns. Equity / Bond / Fund have materially different attributes
// (sector vs maturity/coupon vs TER/AUM) — driving the table from a
// per-type config keeps the rendering logic in one place.

const KINDS = [
  { id: "isin", label: "ISIN" },
  { id: "ticker", label: "Ticker" },
];

const STATUSES = [
  { id: "in_universe", label: "In universe" },
  { id: "watchlist", label: "Watchlist" },
  { id: "excluded", label: "Excluded" },
];

const STATUS_LABEL = Object.fromEntries(STATUSES.map((s) => [s.id, s.label]));

/**
 * @param {object} props
 * @param {"equity"|"bond"|"fund"} props.scope
 * @param {string} props.title       — page header, e.g. "Equity Universe"
 * @param {string} props.subtitle    — one-line explainer under the header
 * @param {{ kind: "isin"|"ticker", value: string }} props.placeholders
 *                                   — per-identifier-kind placeholders
 * @param {Array<{ key: string, label: string, render: (member) => any }>}
 *                  props.columns    — list-table column spec
 * @param {Array<{ label: string, render: (record) => any, mono?: boolean }>}
 *                  props.previewExtras
 *                                   — extra preview-panel rows (after the
 *                                     four shared ones)
 */
export default function UniverseTypePage({
  scope,
  title,
  subtitle,
  placeholders,
  columns,
  previewExtras = [],
}) {
  const [kind, setKind] = useState("isin");
  const [value, setValue] = useState("");

  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);

  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const [members, setMembers] = useState([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState(null);

  const refreshList = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const data = await fetchUniverse({ scope });
      setMembers(data.items || []);
    } catch (err) {
      setListError(err.message);
    } finally {
      setListLoading(false);
    }
  }, [scope]);

  useEffect(() => {
    setKind("isin");
    setValue("");
    setPreview(null);
    setPreviewError(null);
    setMessage(null);
    refreshList();
  }, [refreshList]);

  async function handleFetch(event) {
    event.preventDefault();
    if (!value.trim()) {
      setPreviewError("Identifier value is required");
      return;
    }
    setPreviewLoading(true);
    setPreviewError(null);
    setPreview(null);
    setMessage(null);
    try {
      const result = await assembleInstrument({
        scope,
        kind,
        value: value.trim(),
      });
      setPreview(result);
    } catch (err) {
      setPreviewError(err.message);
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleSave(status) {
    if (!preview) return;
    setSaving(true);
    setMessage(null);
    try {
      const result = await addToUniverse({
        scope: preview.scope,
        kind: preview.identifier.kind,
        value: preview.identifier.value,
        status,
      });
      setMessage(
        `Added ${result.goldenId} as ${STATUS_LABEL[status]} (quality ${result.qualityScore.toFixed(2)})`,
      );
      setPreview(null);
      setValue("");
      await refreshList();
    } catch (err) {
      setMessage(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusChange(member, nextStatus) {
    setMessage(null);
    try {
      await updateUniverseStatus({
        scope: member.scope,
        goldenId: member.goldenId,
        status: nextStatus,
      });
      await refreshList();
    } catch (err) {
      setMessage(`Status update failed: ${err.message}`);
    }
  }

  return (
    <div className="finder">
      <header className="finder-header">
        <h2>{title}</h2>
        <p className="finder-advanced-note">{subtitle}</p>
      </header>

      <section className="finder-detail-section">
        <h3>Add a new {scope}</h3>
        <form
          onSubmit={handleFetch}
          className="finder-fields finder-fields-2"
          style={{ alignItems: "end" }}
        >
          <div className="finder-field">
            <label className="finder-field-label" htmlFor="iu-kind">
              Identifier type
            </label>
            <select
              id="iu-kind"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
            >
              {KINDS.map((k) => (
                <option key={k.id} value={k.id}>
                  {k.label}
                </option>
              ))}
            </select>
          </div>
          <div className="finder-field" style={{ gridColumn: "1 / -1" }}>
            <label className="finder-field-label" htmlFor="iu-value">
              Identifier value
            </label>
            <input
              id="iu-value"
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={placeholders[kind] || ""}
              autoComplete="off"
            />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <button
              type="submit"
              className="btn-primary"
              disabled={previewLoading || !value.trim()}
            >
              {previewLoading ? "Fetching…" : "Fetch"}
            </button>
          </div>
        </form>
        {previewError ? <p className="finder-error">{previewError}</p> : null}
      </section>

      {preview ? (
        <PreviewPanel
          preview={preview}
          extras={previewExtras}
          saving={saving}
          onSave={handleSave}
          onCancel={() => setPreview(null)}
        />
      ) : null}

      {message ? <p className="message">{message}</p> : null}

      <section className="finder-detail-section">
        <h3>
          {title} ({members.length})
        </h3>
        {listLoading ? <p>Loading…</p> : null}
        {listError ? <p className="finder-error">{listError}</p> : null}
        {!listLoading && members.length === 0 ? (
          <p className="finder-empty">
            No {scope} instruments yet. Add your first one above.
          </p>
        ) : null}
        {members.length > 0 ? (
          <UniverseTable
            columns={columns}
            members={members}
            onStatusChange={handleStatusChange}
          />
        ) : null}
      </section>
    </div>
  );
}

function PreviewPanel({ preview, extras, saving, onSave, onCancel }) {
  const [showRaw, setShowRaw] = useState(false);
  const record = preview.record || {};
  const quality = preview.quality_score;
  const gaps = preview.remaining_gaps || [];
  const provenance = preview.provenance || [];

  return (
    <section className="finder-detail-section">
      <div className="finder-detail-header">
        <h3>
          Preview · {record.longName || preview.identifier.value}
          {record.shortName ? <small> ({record.shortName})</small> : null}
        </h3>
        <span className={`status-pill ${qualityClass(quality)}`}>
          quality {quality.toFixed(2)}
        </span>
      </div>

      <dl className="finder-fields finder-fields-2" style={{ marginTop: "0.5rem" }}>
        <PreviewField label="Golden ID" value={record.goldenId} mono />
        <PreviewField label="Currency" value={record.currencyOfDenomination} />
        {extras.map((spec) => (
          <PreviewField
            key={spec.label}
            label={spec.label}
            value={spec.render(record)}
            mono={spec.mono}
          />
        ))}
      </dl>

      <details
        open={gaps.length > 0}
        className="finder-detail-section"
        style={{ marginTop: "0.75rem" }}
      >
        <summary>
          Gaps ({gaps.length}) · Provenance ({provenance.length} sources)
        </summary>
        {gaps.length > 0 ? (
          <p style={{ marginTop: "0.5rem" }}>
            <strong>Missing:</strong>{" "}
            <span className="mono">{gaps.join(", ")}</span>
          </p>
        ) : (
          <p>All planner-relevant fields covered.</p>
        )}
        {provenance.length > 0 ? (
          <ul style={{ marginTop: "0.25rem" }}>
            {provenance.map((p, i) => (
              <li key={i} className="mono">
                {p.fieldGroup} ← {p.source}
              </li>
            ))}
          </ul>
        ) : null}
      </details>

      <details style={{ marginTop: "0.5rem" }} open={showRaw}>
        <summary onClick={() => setShowRaw((v) => !v)}>Raw record</summary>
        <pre
          className="mono"
          style={{
            maxHeight: "20rem",
            overflow: "auto",
            background: "#0e0e0e",
            color: "#e8e8e8",
            padding: "0.75rem",
            fontSize: "0.75rem",
          }}
        >
          {JSON.stringify(record, null, 2)}
        </pre>
      </details>

      <div className="finder-detail-actions" style={{ marginTop: "1rem" }}>
        <button
          type="button"
          className="btn-primary"
          disabled={saving}
          onClick={() => onSave("in_universe")}
        >
          {saving ? "Saving…" : "Add to universe"}
        </button>
        <button
          type="button"
          className="btn-ghost"
          disabled={saving}
          onClick={() => onSave("watchlist")}
        >
          Add to watchlist
        </button>
        <button
          type="button"
          className="btn-ghost"
          disabled={saving}
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
    </section>
  );
}

function PreviewField({ label, value, mono = false }) {
  return (
    <div className="finder-field">
      <span className="finder-field-label">{label}</span>
      <span className={mono ? "mono" : ""}>
        {value || <em style={{ opacity: 0.5 }}>—</em>}
      </span>
    </div>
  );
}

function UniverseTable({ columns, members, onStatusChange }) {
  return (
    <table className="universe-table">
      <thead>
        <tr>
          {columns.map((col) => (
            <th key={col.key}>{col.label}</th>
          ))}
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {members.map((m) => (
          <tr key={`${m.scope}:${m.goldenId}`}>
            {columns.map((col) => (
              <td key={col.key} className={col.mono ? "mono" : ""}>
                {renderCell(col.render(m))}
              </td>
            ))}
            <td>
              <select
                value={m.universeStatus}
                onChange={(e) => onStatusChange(m, e.target.value)}
              >
                {STATUSES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function renderCell(value) {
  if (value === null || value === undefined || value === "") {
    return <em style={{ opacity: 0.4 }}>—</em>;
  }
  return value;
}

function qualityClass(q) {
  if (q >= 0.85) return "ok";
  if (q >= 0.5) return "warn";
  return "bad";
}

export function formatPercent(decimal) {
  if (decimal === null || decimal === undefined) return null;
  return `${(decimal * 100).toFixed(2)} %`;
}

export function formatQuality(q) {
  if (q === null || q === undefined) return null;
  return q.toFixed(2);
}
