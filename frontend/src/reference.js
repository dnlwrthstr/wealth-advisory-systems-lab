/**
 * OpenWealth reference data — loaded once from GET /custody/reference.
 *
 * Usage:
 *   await loadReferenceData();          // call once at app startup
 *   labelFor("customerSegment", "highNetWorth")  // → "High Net Worth"
 *   optionsFor("investmentStrategy")             // → [{value, label}, ...]
 */

import { fetchReferenceData } from "./services/api";

// Module-level cache — survives re-renders, shared across the whole app
let _data = null;

export async function loadReferenceData() {
  if (_data) return _data;
  try {
    _data = await fetchReferenceData();
  } catch {
    _data = {};
  }
  return _data;
}

/**
 * Return the human-readable label for a value in a reference category.
 * Falls back to the raw value if the category or value isn't found.
 */
export function labelFor(category, value) {
  if (!_data || value == null) return value ?? "—";
  const entry = _data[category]?.find((item) => item.value === value);
  return entry?.label ?? value;
}

/**
 * Return all options for a category as [{value, label}] for use in <select>.
 * Returns [] before reference data has loaded.
 */
export function optionsFor(category) {
  return _data?.[category] ?? [];
}

/**
 * Return the raw loaded reference map (all categories).
 * Useful when a component needs to iterate over multiple categories.
 */
export function referenceData() {
  return _data ?? {};
}
