"""HTTP surface for tariff inspection and calculation."""

from fastapi.testclient import TestClient


def test_tariff_catalog_lists_metadata_and_unavailable_companies(client: TestClient) -> None:
    response = client.get("/api/tariffs")

    assert response.status_code == 200
    body = response.json()
    configs = {item["config_id"]: item for item in body["configurations"]}
    assert set(configs) == {
        "iesco-a1-residential-non-tou-lifeline-sro-279-2026",
        "iesco-a1-residential-non-tou-unprotected-sro-279-2026",
        "iesco-a1-residential-tou-sro-279-2026",
    }
    assert all(item["payable_total_available"] is False for item in configs.values())
    assert all(item["synthetic"] is False for item in configs.values())
    assert all(item["source"]["source_url"] == "https://iesco.com.pk/tariff-guide" for item in configs.values())
    unavailable = {(item["provider_code"], item["status"]) for item in body["unavailable"]}
    assert ("LESCO", "unavailable") in unavailable
    assert ("KE", "unavailable") in unavailable
    assert ("IESCO", "needs_verification") in unavailable
    for entry in body["unavailable"]:
        assert "rate_per_kwh" not in entry
        assert "slabs" not in entry


def test_resolve_returns_the_verified_file_for_a_covered_date(client: TestClient) -> None:
    response = client.get(
        "/api/tariffs/resolve",
        params={
            "provider_code": "iesco",
            "consumer_category": "Residential",
            "tariff_type": "non_tou",
            "eligibility": "unprotected",
            "billing_date": "2026-03-01",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "matched"
    assert body["configuration"]["config_id"] == "iesco-a1-residential-non-tou-unprotected-sro-279-2026"
    assert body["configuration"]["slab_method"] == "single_slab"


def test_resolve_before_the_effective_date_is_unavailable(client: TestClient) -> None:
    response = client.get(
        "/api/tariffs/resolve",
        params={
            "provider_code": "IESCO",
            "consumer_category": "residential",
            "tariff_type": "non_tou",
            "eligibility": "unprotected",
            "billing_date": "2026-02-11",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "unavailable"
    assert body["reason_code"] == "no_applicable_configuration"
    assert body["configuration"] is None


def test_valid_calculation_returns_components_without_a_payable_total(client: TestClient) -> None:
    response = client.post(
        "/api/tariffs/calculations",
        json={
            "provider_code": "IESCO",
            "consumer_category": "residential",
            "tariff_type": "non_tou",
            "eligibility": "unprotected",
            "billing_date": "2026-03-01",
            "consumption_kwh": "250",
            "sanctioned_load_kw": "5",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "unavailable"
    assert body["trust_status"] == "Unavailable"
    assert body["final_amount"] is None
    amounts = {item["code"]: item for item in body["components"]}
    assert amounts["energy_charge"]["amount"] == "8275.00"
    assert amounts["energy_charge"]["trust_status"] == "Calculated"
    assert isinstance(amounts["energy_charge"]["amount"], str)
    assert amounts["fixed_charge"]["amount"] == "1750.00"
    assert amounts["gst"]["amount"] is None
    assert "Estimated" not in response.text


def test_invalid_calculation_rejects_a_binary_float(client: TestClient) -> None:
    response = client.post(
        "/api/tariffs/calculations",
        json={
            "provider_code": "IESCO",
            "consumer_category": "residential",
            "tariff_type": "non_tou",
            "eligibility": "unprotected",
            "billing_date": "2026-03-01",
            "consumption_kwh": 250.5,
            "sanctioned_load_kw": "5",
        },
    )

    assert response.status_code == 422


def test_unknown_provider_calculation_is_unavailable(client: TestClient) -> None:
    response = client.post(
        "/api/tariffs/calculations",
        json={
            "provider_code": "HESCO",
            "consumer_category": "residential",
            "tariff_type": "non_tou",
            "eligibility": "unprotected",
            "billing_date": "2026-03-01",
            "consumption_kwh": "250",
            "sanctioned_load_kw": "5",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reason_code"] == "unsupported_provider"
    assert body["final_amount"] is None
    assert body["components"] == []
    assert body["trust_status"] == "Unavailable"


def test_missing_sanctioned_load_is_reported(client: TestClient) -> None:
    response = client.post(
        "/api/tariffs/calculations",
        json={
            "provider_code": "IESCO",
            "consumer_category": "residential",
            "tariff_type": "non_tou",
            "eligibility": "unprotected",
            "billing_date": "2026-03-01",
            "consumption_kwh": "250",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reason_code"] == "missing_input"
    assert body["missing_inputs"] == ["sanctioned_load_kw"]
    assert body["final_amount"] is None
    assert body["trust_status"] == "Unavailable"


def test_invalid_resolution_query_is_a_field_error(client: TestClient) -> None:
    response = client.get(
        "/api/tariffs/resolve",
        params={
            "provider_code": "IESCO",
            "consumer_category": "residential",
            "tariff_type": "non_tou",
            "billing_date": "not-a-date",
        },
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_tariff_route_keeps_the_existing_cors_policy(client: TestClient) -> None:
    allowed = client.get("/api/tariffs", headers={"Origin": "http://localhost:3000"})
    rejected = client.get("/api/tariffs", headers={"Origin": "https://unknown.example"})

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert rejected.headers.get("access-control-allow-origin") is None
