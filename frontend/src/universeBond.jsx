import React from "react";
import UniverseTypePage, { formatPercent, formatQuality } from "./universePage";

const COLUMNS = [
  { key: "name", label: "Name", render: (m) => m.longName },
  { key: "isin", label: "ISIN", mono: true, render: (m) => m.isin },
  { key: "currency", label: "CCY", render: (m) => m.currency },
  { key: "coupon", label: "Coupon", mono: true, render: (m) => formatPercent(m.couponRate) },
  { key: "maturity", label: "Maturity", mono: true, render: (m) => m.maturityDate },
  { key: "seniority", label: "Seniority", render: (m) => m.seniority },
  { key: "quality", label: "Quality", mono: true, render: (m) => formatQuality(m.qualityScore) },
];

const PREVIEW_EXTRAS = [
  { label: "Issuer", render: (r) => (r.issuer || {}).legalName },
  { label: "Maturity", mono: true, render: (r) => r.maturityDate },
  { label: "Coupon", mono: true, render: (r) => formatPercent(r.currentCouponRate) },
  { label: "Coupon type", render: (r) => r.couponType },
  { label: "Seniority", render: (r) => r.seniority },
  {
    label: "Primary listing",
    render: (r) => (r.primaryListing ? r.primaryListing.mic || null : null),
  },
];

export default function BondUniversePage() {
  return (
    <UniverseTypePage
      scope="bond"
      title="Bond Universe"
      subtitle="Fixed-income instruments assembled from ESMA FIRDS with curated issuer-LEI mapping."
      placeholders={{ isin: "e.g. XS2434891219", ticker: "" }}
      columns={COLUMNS}
      previewExtras={PREVIEW_EXTRAS}
    />
  );
}
