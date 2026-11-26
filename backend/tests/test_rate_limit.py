"""The file-check limiter ignores a spoofed forwarding header and drops stale keys."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.rate_limit import ExtractRateLimiter, client_address
from app.main import create_app

JPEG = b"\xff\xd8\xff" + b"\x00" * 16 + b"\xff\xd9"


def test_spoofed_forwarding_header_does_not_change_the_client() -> None:
    assert client_address("203.0.113.8", "198.51.100.9", frozenset()) == "203.0.113.8"
    assert client_address(None, "198.51.100.9", frozenset()) == "local"


def test_trusted_proxy_uses_the_rightmost_untrusted_address() -> None:
    trusted = frozenset({"10.0.0.1", "10.0.0.2"})

    assert client_address("10.0.0.1", "203.0.113.8", trusted) == "203.0.113.8"
    assert (
        client_address("10.0.0.1", "198.51.100.9, 203.0.113.8, 10.0.0.2", trusted)
        == "203.0.113.8"
    )
    assert client_address("203.0.113.8", "198.51.100.9", trusted) == "203.0.113.8"


def test_limiter_drops_stale_keys_and_stops_growing() -> None:
    limiter = ExtractRateLimiter(2, max_keys=2)
    assert limiter.allow("one", now=0)
    assert limiter.allow("two", now=1)
    assert limiter.allow("three", now=2) is False
    assert limiter.allow("one", now=61)
    assert "two" not in limiter._hits
    assert limiter.allow("three", now=62)


def test_spoofed_header_cannot_reset_the_http_limit() -> None:
    app = create_app(
        Settings(
            app_env="test",
            cors_origins=["http://localhost:3000"],
            extract_rate_limit_per_minute=1,
            trusted_proxies=[],
        )
    )
    with TestClient(app) as client:
        first = client.post(
            "/api/bills/extractions",
            files={"file": ("bill.jpg", JPEG, "image/jpeg")},
            headers={"X-Forwarded-For": "198.51.100.9"},
        )
        second = client.post(
            "/api/bills/extractions",
            files={"file": ("bill.jpg", JPEG, "image/jpeg")},
            headers={"X-Forwarded-For": "198.51.100.10"},
        )

    assert first.status_code != 429
    assert second.status_code == 429
    assert second.json()["code"] == "unavailable"


def test_trusted_proxy_limits_the_forwarded_client() -> None:
    app = create_app(
        Settings(
            app_env="test",
            cors_origins=["http://localhost:3000"],
            extract_rate_limit_per_minute=1,
            trusted_proxies=["10.0.0.1"],
        )
    )
    with TestClient(app, client=("10.0.0.1", 50000)) as client:
        first = client.post(
            "/api/bills/extractions",
            files={"file": ("bill.jpg", JPEG, "image/jpeg")},
            headers={"X-Forwarded-For": "203.0.113.8"},
        )
        other_client = client.post(
            "/api/bills/extractions",
            files={"file": ("bill.jpg", JPEG, "image/jpeg")},
            headers={"X-Forwarded-For": "203.0.113.9"},
        )
        same_client = client.post(
            "/api/bills/extractions",
            files={"file": ("bill.jpg", JPEG, "image/jpeg")},
            headers={"X-Forwarded-For": "203.0.113.8"},
        )

    assert first.status_code != 429
    assert other_client.status_code != 429
    assert same_client.status_code == 429
