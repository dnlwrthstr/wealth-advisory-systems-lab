const API_BASE = "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with ${response.status}`);
  }

  return response.json();
}

export function listQuestionnaires() {
  return request("/admin/questionnaires");
}

export function fetchQuestionnaire(questionnaireId) {
  return request(`/admin/questionnaires/${questionnaireId}`);
}

export function saveQuestionnaire(questionnaire) {
  return request("/admin/questionnaires", {
    method: "POST",
    body: JSON.stringify(questionnaire),
  });
}

export function processAnswers(questionnaireId, payload) {
  return request(`/admin/questionnaires/${questionnaireId}/process`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listClientSegments() {
  return request("/admin/client-segments");
}

export function saveClientSegment(segment) {
  return request("/admin/client-segments", {
    method: "POST",
    body: JSON.stringify(segment),
  });
}

export function listCustodyCustomers() {
  return request("/custody/customers");
}

export function fetchCustodyCustomer(customerId) {
  return request(`/custody/customers/${customerId}`);
}

export function fetchCustodyAccounts(customerId) {
  return request(`/custody/customers/${customerId}/accounts`);
}

export function fetchCustodyPositions(customerId, accountId = null) {
  const qs = accountId ? `?account_id=${encodeURIComponent(accountId)}` : "";
  return request(`/custody/customers/${customerId}/positions${qs}`);
}

export function fetchCustodyTransactions(customerId) {
  return request(`/custody/customers/${customerId}/transactions`);
}

export function fetchCustodySnapshot(customerId) {
  return request(`/custody/customers/${customerId}/snapshot`);
}

export function fetchClientProfile(clientId) {
  return request(`/profile/${clientId}`);
}

export function fetchReferenceData() {
  return request("/custody/reference");
}

// Instrument API
export function searchInstruments({ q = "", type = null, currency = null, limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams({ q, limit, offset });
  if (type) params.set("type", type);
  if (currency) params.set("currency", currency);
  return request(`/instruments?${params}`);
}

export function fetchInstrumentTypes() {
  return request("/instruments/types");
}

export function fetchInstrument(instrumentId) {
  return request(`/instruments/${instrumentId}`);
}

// Order API
export function submitOrder(payload) {
  return request("/orders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listPortfolioOrders(portfolioId) {
  return request(`/orders/portfolio/${portfolioId}`);
}

export function fetchOrder(orderId) {
  return request(`/orders/${orderId}`);
}

export function cancelOrder(orderId) {
  return request(`/orders/${orderId}`, { method: "DELETE" });
}

export function listAllOrders({ status = null, portfolio_id = null } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (portfolio_id) params.set("portfolio_id", portfolio_id);
  const qs = params.toString();
  return request(`/orders${qs ? "?" + qs : ""}`);
}

export function getOrderMode() {
  return request("/orders/mode");
}

export function setOrderMode(auto) {
  return request("/orders/mode", {
    method: "POST",
    body: JSON.stringify({ auto }),
  });
}

export function manualExecuteOrder(orderId) {
  return request(`/orders/${orderId}/execute`, { method: "POST" });
}
