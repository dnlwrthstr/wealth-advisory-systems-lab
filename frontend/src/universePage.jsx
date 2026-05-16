import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  addToUniverse,
  assembleInstrument,
  fetchInstrumentDocument,
  fetchUniverse,
  updateUniverseStatus,
} from "./services/api";
import { DetailSection, OrderDialog } from "./instruments";

// Unified Investment Universe page. Filter tabs (All / Equity / Bond / Fund)
// drive both the listing and the "Add new" form (Add is disabled on All —
// scope is required to call the agentic platform). Clicking a list row
// fetches the full per-security document and renders the same DetailSection
// used by the Find-an-instrument view.

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

const TYPE_TABS = [
  { id: "all", label: "All" },
  { id: "equity", label: "Equity" },
  { id: "bond", label: "Bond" },
  { id: "fund", label: "Fund" },
];

const SCOPE_PLACEHOLDERS = {
  equity: { isin: "e.g. CH0012221716", ticker: "e.g. ABBN.SW" },
  bond: { isin: "e.g. XS2434891219", ticker: "" },
  fund: { isin: "e.g. IE00B4L5Y983", ticker: "" },
};

function fmtPercent(decimal) {
  if (decimal === null || decimal === undefined) return null;
  return `${(decimal * 100).toFixed(2)} %`;
}

function fmtQuality(q) {
  if (q === null || q === undefined) return null;
  return q.toFixed(2);
}

// Per-scope column specs for the listing table. The "All" tab uses a
// compact common subset plus a Type chip.
const COLUMNS = {
  all: [
    { key: "type", label: "Type", render: (m) => <span className="finder-row-chip">{labelForScope(m.scope)}</span> },
    { key: "name", label: "Name", render: (m) => m.longName },
    { key: "isin", label: "ISIN", mono: true, render: (m) => m.isin },
    { key: "currency", label: "CCY", render: (m) => m.currency },
    { key: "quality", label: "Quality", mono: true, render: (m) => fmtQuality(m.qualityScore) },
  ],
  equity: [
    { key: "name", label: "Name", render: (m) => m.longName },
    { key: "isin", label: "ISIN", mono: true, render: (m) => m.isin },
    { key: "ticker", label: "Ticker", mono: true, render: (m) => m.ticker },
    { key: "currency", label: "CCY", render: (m) => m.currency },
    { key: "sector", label: "Sector", render: (m) => m.sector },
    { key: "quality", label: "Quality", mono: true, render: (m) => fmtQuality(m.qualityScore) },
  ],
  bond: [
    { key: "name", label: "Name", render: (m) => m.longName },
    { key: "isin", label: "ISIN", mono: true, render: (m) => m.isin },
    { key: "currency", label: "CCY", render: (m) => m.currency },
    { key: "coupon", label: "Coupon", mono: true, render: (m) => fmtPercent(m.couponRate) },
    { key: "maturity", label: "Maturity", mono: true, render: (m) => m.maturityDate },
    { key: "seniority", label: "Seniority", render: (m) => m.seniority },
    { key: "quality", label: "Quality", mono: true, render: (m) => fmtQuality(m.qualityScore) },
  ],
  fund: [
    { key: "name", label: "Name", render: (m) => m.longName },
    { key: "isin", label: "ISIN", mono: true, render: (m) => m.isin },
    { key: "currency", label: "CCY", render: (m) => m.currency },
    { key: "ter", label: "TER", mono: true, render: (m) => fmtPercent(m.totalExpenseRatio) },
    { key: "mgmt", label: "Mgmt Company", render: (m) => m.managementCompany },
    { key: "quality", label: "Quality", mono: true, render: (m) => fmtQuality(m.qualityScore) },
  ],
};

const PREVIEW_EXTRAS = {
  equity: [
    {
      label: "Primary listing",
      render: (r) =>
        r.primaryListing
          ? `${r.primaryListing.mic || "?"} · ${r.primaryListing.ticker || "?"}`
          : null,
    },
    { label: "Issuer", render: (r) => (r.issuer || {}).legalName },
    {
      label: "Sector",
      render: (r) => {
        const s = r.industrySector || {};
        return s.sectorLabel
          ? `${s.sectorLabel}${s.industryLabel ? ` · ${s.industryLabel}` : ""}`
          : null;
      },
    },
    {
      label: "Market cap",
      render: (r) => {
        const cap = (r.keyFigures || {}).marketCapitalisation;
        return cap ? cap.toLocaleString() : null;
      },
    },
  ],
  bond: [
    { label: "Issuer", render: (r) => (r.issuer || {}).legalName },
    { label: "Maturity", mono: true, render: (r) => r.maturityDate },
    { label: "Coupon", mono: true, render: (r) => fmtPercent(r.currentCouponRate) },
    { label: "Coupon type", render: (r) => r.couponType },
    { label: "Seniority", render: (r) => r.seniority },
    {
      label: "Primary listing",
      render: (r) => (r.primaryListing ? r.primaryListing.mic || null : null),
    },
  ],
  fund: [
    { label: "Umbrella", render: (r) => (r.umbrella || {}).legalName },
    { label: "Management company", render: (r) => (r.managementCompany || {}).legalName },
    { label: "Promoter", render: (r) => (r.promoter || {}).legalName },
    { label: "TER", mono: true, render: (r) => fmtPercent(r.totalExpenseRatio) },
    { label: "Asset class", render: (r) => r.assetClass },
    {
      label: "Primary listing",
      render: (r) =>
        r.primaryListing
          ? `${r.primaryListing.mic || "?"}${r.primaryListing.ticker ? ` · ${r.primaryListing.ticker}` : ""}`
          : null,
    },
  ],
};

function labelForScope(scope) {
  return ({ equity: "Equity", bond: "Bond", fund: "Fund" })[scope] || scope;
}

export default function UniversePage() {
  const [typeTab, setTypeTab] = useState("all");

  // Add-new form state (only meaningful when a concrete scope is selected).
  const [kind, setKind] = useState("isin");
  const [value, setValue] = useState("");

  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);

  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  // Listing state.
  const [members, setMembers] = useState([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState(null);

  // Detail-view state.
  const [selectedMember, setSelectedMember] = useState(null);
  const [docSource, setDocSource] = useState(null);
  const [docLoading, setDocLoading] = useState(false);
  const [showOrder, setShowOrder] = useState(false);

  const isAll = typeTab === "all";

  const refreshList = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const data = await fetchUniverse(isAll ? {} : { scope: typeTab });
      setMembers(data.items || []);
    } catch (err) {
      setListError(err.message);
    } finally {
      setListLoading(false);
    }
  }, [typeTab, isAll]);

  useEffect(() => {
    setKind("isin");
    setValue("");
    setPreview(null);
    setPreviewError(null);
    setMessage(null);
    setSelectedMember(null);
    setDocSource(null);
    setShowOrder(false);
    refreshList();
  }, [refreshList]);

  // Fetch the full per-security document whenever the selection changes.
  useEffect(() => {
    if (!selectedMember) {
      setDocSource(null);
      return;
    }
    let alive = true;
    setDocLoading(true);
    fetchInstrumentDocument(selectedMember.scope, selectedMember.goldenId)
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
  }, [selectedMember?.scope, selectedMember?.goldenId]);

  async function handleFetch(event) {
    event.preventDefault();
    if (isAll) return;
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
        scope: typeTab,
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

  const columns = COLUMNS[typeTab] || COLUMNS.all;
  const placeholders = SCOPE_PLACEHOLDERS[typeTab] || {};
  const previewExtras = preview ? (PREVIEW_EXTRAS[preview.scope] || []) : [];

  // Build a hit-like object so DetailSection (which expects the search-hit
  // shape from /instruments/search) can render against a universe member.
  const detailHit = useMemo(() => {
    if (!selectedMember) return null;
    return {
      scope: selectedMember.scope,
      document_id: selectedMember.goldenId,
      long_name: selectedMember.longName || selectedMember.goldenId,
      asset_class: labelForScope(selectedMember.scope),
    };
  }, [selectedMember]);

  return (
    <div className="finder">
      <header className="finder-header">
        <h2>Investment Universe</h2>
        <p className="finder-advanced-note">
          Instruments managed in the universe — assembled via the agentic platform
          (OpenFIGI, Yahoo, FIRDS, GLEIF, factsheet skill). Use the tabs to filter
          by type. Click a row for the full record.
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
      </header>

      {!isAll && (
        <section className="finder-detail-section">
          <h3>Add a new {typeTab}</h3>
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
      )}

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
          {isAll ? "All instruments" : `${labelForScope(typeTab)} instruments`}
          {" "}({members.length})
        </h3>
        {listLoading ? <p>Loading…</p> : null}
        {listError ? <p className="finder-error">{listError}</p> : null}
        {!listLoading && members.length === 0 ? (
          <p className="finder-empty">
            No {isAll ? "instruments" : typeTab} in the universe yet
            {isAll ? "" : " — add your first one above"}.
          </p>
        ) : null}
        {members.length > 0 ? (
          <UniverseTable
            columns={columns}
            members={members}
            selectedId={selectedMember?.goldenId || null}
            selectedScope={selectedMember?.scope || null}
            onSelect={setSelectedMember}
            onStatusChange={handleStatusChange}
          />
        ) : null}
      </section>

      {detailHit && (
        <DetailSection
          hit={detailHit}
          source={docSource}
          loading={docLoading}
          onClose={() => setSelectedMember(null)}
          onTrade={() => setShowOrder(true)}
        />
      )}

      {showOrder && selectedMember && (
        <OrderDialog
          isin={selectedMember.isin || ""}
          instrumentName={selectedMember.longName || selectedMember.goldenId}
          currency={selectedMember.currency || ""}
          suggestedPrice={null}
          portfolioId=""
          accountId=""
          onClose={() => setShowOrder(false)}
        />
      )}
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

function UniverseTable({
  columns,
  members,
  selectedId,
  selectedScope,
  onSelect,
  onStatusChange,
}) {
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
        {members.map((m) => {
          const isSelected =
            m.goldenId === selectedId && m.scope === selectedScope;
          return (
            <tr
              key={`${m.scope}:${m.goldenId}`}
              className={isSelected ? "selected" : ""}
              onClick={() => onSelect(m)}
              style={{ cursor: "pointer" }}
            >
              {columns.map((col) => (
                <td key={col.key} className={col.mono ? "mono" : ""}>
                  {renderCell(col.render(m))}
                </td>
              ))}
              <td onClick={(e) => e.stopPropagation()}>
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
          );
        })}
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
