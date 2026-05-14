from fastapi.testclient import TestClient

from backend.custodian_api.main import app


client = TestClient(app)


def test_custody_snapshot_endpoint_returns_openwealth_style_data():
    response = client.get("/custody/customers/C-1001/snapshot")

    assert response.status_code == 200
    body = response.json()
    # OpenWealth uses camelCase aliases; Customer.id serialises as "id"
    assert body["customer"]["id"] == "C-1001"
    assert len(body["accounts"]) == 2   # A-1001-SEC, A-1001-CASH
    assert len(body["positions"]) == 5  # 4 securities + 1 cash
    assert body["baseCurrency"] == "CHF"


def test_missing_custody_customer_returns_404():
    response = client.get("/custody/customers/not-real/snapshot")

    assert response.status_code == 404
