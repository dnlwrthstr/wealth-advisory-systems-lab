from fastapi.testclient import TestClient

from backend.profile_api.main import app


client = TestClient(app)


def test_admin_lists_client_segments():
    response = client.get("/admin/client-segments")

    assert response.status_code == 200
    segment_ids = {segment["segment_id"] for segment in response.json()}
    assert {"private_client", "hnw", "family_office"}.issubset(segment_ids)


def test_admin_saves_client_segment():
    payload = {
        "segment_id": "entrepreneur",
        "label": "Entrepreneur",
        "description": "Business owner with concentrated wealth and liquidity-event planning.",
        "minimum_liquid_net_worth": 750000,
        "default_questionnaire_id": "client_profile_v1",
        "review_policy": "enhanced",
        "enabled": True,
    }

    response = client.post("/admin/client-segments", json=payload)

    assert response.status_code == 200
    assert response.json()["segment_id"] == "entrepreneur"

    list_response = client.get("/admin/client-segments")
    segment_ids = {segment["segment_id"] for segment in list_response.json()}
    assert "entrepreneur" in segment_ids
