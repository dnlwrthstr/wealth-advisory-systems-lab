import React, { useCallback, useEffect, useState } from "react";
import {
  addToUniverse,
  assembleInstrument,
  fetchUniverse,
  updateUniverseStatus,
} from "./services/api";

const SCOPES = [
  { id: "equity", label: "Equity" },
  { id: "bond", label: "Bond" },
  { id: "fund", label: "Fund" },
];

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

export default function InvestmentUniverseApp() {
  // Add form state
  const [scope, setScope] = useState("equity");
  const [kind, setKind] = useState("isin");
  const [value, setValue] = useState("");

  // Preview state (the assembled-but-not-yet-persisted record)
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);

  // Save state
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  // Universe list
  const [members, setMembers] = useState([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState(null);

  const refreshList = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const data = await fetchUniverse({});
      setMembers(data.items || []);
    } catch (err) {
      setListError(err.message);
    } finally {
      setListLoading(false);
    }
  }, []);

  useEffect(() => {
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
        <h2>Investment Universe</h2>
        <p className="finder-advanced-note">
          Build your PMS universe one instrument at a time. Enter an identifier,
          let the agentic platform assemble what it can find, then add the
          result to the universe or to a watchlist.
        </p>
      </header>

      <section className="finder-detail-section">
        <h3>Add a new instrument</h3>
        <form
          onSubmit={handleFetch}
          className="finder-fields finder-fields-2"
          style={{ alignItems: "end" }}
        >
          <div className="finder-field">
            <label className="finder-field-label" htmlFor="iu-scope">
              Scope
            </label>
            <select
              id="iu-scope"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
            >
              {SCOPES.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
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
              placeholder={kind === "isin" ? "e.g. CH0012221716" : "e.g. ABBN.SW"}
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
          saving={saving}
          onSave={handleSave}
          onCancel={() => setPreview(null)}
        />
      ) : null}

      {message ? <p className="message">{message}</p> : null}

      <section className="finder-detail-section">
        <h3>Universe members ({members.length})</h3>
        {listLoading ? <p>Loading…</p> : null}
        {listError ? <p className="finder-error">{listError}</p> : null}
        {!listLoading && members.length === 0 ? (
          <p className="finder-empty">No instruments yet. Add your first one above.</p>
        ) : null}
        {members.length > 0 ? (
          <UniverseTable
            members={members}
            onStatusChange={handleStatusChange}
          />
        ) : null}
      </section>
    </div>
  );
}

function PreviewPanel({ preview, saving, onSave, onCancel }) {
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
        <PreviewField label="Scope" value={preview.scope} />
        <PreviewField label="Golden ID" value={record.goldenId} mono />
        <PreviewField label="Currency" value={record.currencyOfDenomination} />
        <PreviewField
          label="Primary listing"
          value={
            record.primaryListing
              ? `${record.primaryListing.mic || "?"} · ${record.primaryListing.ticker || "?"}`
              : null
          }
        />
        <PreviewField
          label="Issuer"
          value={(record.issuer || {}).legalName}
        />
        <PreviewField
          label="Industry"
          value={
            (record.industrySector || {}).sectorLabel
              ? `${record.industrySector.sectorLabel} · ${record.industrySector.industryLabel || ""}`.trim()
              : null
          }
        />
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

function UniverseTable({ members, onStatusChange }) {
  return (
    <table className="universe-table">
      <thead>
        <tr>
          <th>Scope</th>
          <th>Name</th>
          <th>ISIN</th>
          <th>Ticker</th>
          <th>CCY</th>
          <th>Quality</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {members.map((m) => (
          <tr key={`${m.scope}:${m.goldenId}`}>
            <td>{m.scope}</td>
            <td>{m.longName || <em style={{ opacity: 0.5 }}>—</em>}</td>
            <td className="mono">{m.isin || ""}</td>
            <td className="mono">{m.ticker || ""}</td>
            <td>{m.currency || ""}</td>
            <td className="mono">{m.qualityScore?.toFixed(2) || ""}</td>
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

function qualityClass(q) {
  if (q >= 0.85) return "ok";
  if (q >= 0.5) return "warn";
  return "bad";
}
