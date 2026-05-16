import React from "react";
import UniverseTypePage, { formatQuality } from "./universePage";

const COLUMNS = [
  { key: "name", label: "Name", render: (m) => m.longName },
  { key: "isin", label: "ISIN", mono: true, render: (m) => m.isin },
  { key: "ticker", label: "Ticker", mono: true, render: (m) => m.ticker },
  { key: "currency", label: "CCY", render: (m) => m.currency },
  { key: "sector", label: "Sector", render: (m) => m.sector },
  { key: "quality", label: "Quality", mono: true, render: (m) => formatQuality(m.qualityScore) },
];

const PREVIEW_EXTRAS = [
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
];

export default function EquityUniversePage() {
  return (
    <UniverseTypePage
      scope="equity"
      title="Equity Universe"
      subtitle="Stocks assembled via OpenFIGI, Yahoo, FIRDS and SIX ticker map."
      placeholders={{ isin: "e.g. CH0012221716", ticker: "e.g. ABBN.SW" }}
      columns={COLUMNS}
      previewExtras={PREVIEW_EXTRAS}
    />
  );
}
