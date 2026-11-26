from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.integrations.gemini.client import GoogleGeminiExtractor
from app.integrations.gemini.errors import GeminiNotConfigured, GeminiSchemaError, GeminiTimeout, GeminiUnavailable
from tests.bill_samples import extraction_payload


class TimeoutError(Exception):
    """Named like the SDK timeout so the client maps it without a network call."""


def _settings(key: str | None = "test-key") -> Settings:
    return Settings(app_env="test", gemini_api_key=key, gemini_model="gemini-3.8-flash", cors_origins=["http://localhost:3000"])


def test_missing_key_does_not_call_the_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("Gemini client was constructed")

    monkeypatch.setattr("google.genai.Client", boom)
    with pytest.raises(GeminiNotConfigured):
        GoogleGeminiExtractor(_settings(None)).extract_document(b"png", "image/png")


def test_timeout_invalid_json_and_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class Interactions:
        @staticmethod
        def create(**kwargs: object) -> SimpleNamespace:
            calls.append(kwargs)
            if len(calls) == 1:
                raise TimeoutError("slow")
            if len(calls) == 2:
                raise RuntimeError("secret bill text")
            if len(calls) == 3:
                return SimpleNamespace(output_text="[")
            return SimpleNamespace(output_text="[1, 2]")

    class Client:
        def __init__(self, **kwargs: object) -> None:
            assert "test-key" == kwargs["api_key"]
            self.interactions = Interactions()

    monkeypatch.setattr("google.genai.Client", Client)
    extractor = GoogleGeminiExtractor(_settings())

    with pytest.raises(GeminiTimeout):
        extractor.extract_document(b"timeout-marker", "image/png")
    with pytest.raises(GeminiUnavailable):
        extractor.extract_document(b"down-marker", "application/pdf")
    with pytest.raises(GeminiSchemaError):
        extractor.extract_document(b"bad-json", "image/png")
    with pytest.raises(GeminiSchemaError):
        extractor.extract_document(b"shape", "image/png")

    assert calls[0]["model"] == "gemini-3.8-flash"
    assert calls[0]["store"] is False
    assert calls[1]["input"][1]["type"] == "document"
    assert "secret bill text" not in "".join(calls[0]["input"][0]["text"])


def test_valid_structured_response_is_returned_without_logging_the_document(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    payload = extraction_payload()

    class Interactions:
        @staticmethod
        def create(**kwargs: object) -> SimpleNamespace:
            import json

            return SimpleNamespace(output_text=json.dumps(payload))

    class Client:
        def __init__(self, **kwargs: object) -> None:
            self.interactions = Interactions()

    monkeypatch.setattr("google.genai.Client", Client)
    with caplog.at_level("ERROR"):
        result = GoogleGeminiExtractor(_settings()).extract_document(b"private-bill", "image/jpeg")

    assert result["provider_code"]["value"] == "IESCO"
    assert "private-bill" not in caplog.text
    assert "test-key" not in caplog.text
