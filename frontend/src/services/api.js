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
