import React from "react";
import UniverseTypePage, { formatPercent, formatQuality } from "./universePage";

const COLUMNS = [
  { key: "name", label: "Name", render: (m) => m.longName },
  { key: "isin", label: "ISIN", mono: true, render: (m) => m.isin },
  { key: "currency", label: "CCY", render: (m) => m.currency },
  { key: "ter", label: "TER", mono: true, render: (m) => formatPercent(m.totalExpenseRatio) },
  { key: "mgmt", label: "Mgmt Company", render: (m) => m.managementCompany },
  { key: "quality", label: "Quality", mono: true, render: (m) => formatQuality(m.qualityScore) },
];

const PREVIEW_EXTRAS = [
  { label: "Umbrella", render: (r) => (r.umbrella || {}).legalName },
  { label: "Management company", render: (r) => (r.managementCompany || {}).legalName },
  { label: "Promoter", render: (r) => (r.promoter || {}).legalName },
  { label: "TER", mono: true, render: (r) => formatPercent(r.totalExpenseRatio) },
  { label: "Asset class", render: (r) => r.assetClass },
  {
    label: "Primary listing",
    render: (r) =>
      r.primaryListing
        ? `${r.primaryListing.mic || "?"}${r.primaryListing.ticker ? ` · ${r.primaryListing.ticker}` : ""}`
        : null,
  },
];

export default function FundUniversePage() {
  return (
    <UniverseTypePage
      scope="fund"
      title="Fund Universe"
      subtitle="UCITS funds and ETFs assembled from FIRDS, Yahoo, and the factsheet skill (LLM)."
      placeholders={{ isin: "e.g. IE00B4L5Y983", ticker: "" }}
      columns={COLUMNS}
      previewExtras={PREVIEW_EXTRAS}
    />
  );
}
