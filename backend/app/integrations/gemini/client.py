"""Call Gemini with an in-memory document. The document is not stored with the API."""

import json
import logging
from base64 import b64encode
from typing import Protocol

from app.core.config import Settings
from app.integrations.gemini.errors import (
    GeminiError,
    GeminiNotConfigured,
    GeminiSchemaError,
    GeminiTimeout,
    GeminiUnavailable,
)
logger = logging.getLogger("bijlibachat.gemini")


class DocumentExtractor(Protocol):
    def extract_document(self, content: bytes, mime_type: str) -> dict[str, object]:
        """Return the model's JSON object. Do not log the document."""


class GoogleGeminiExtractor:
    """Official google-genai client. Inline bytes avoid a stored file upload."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def extract_document(self, content: bytes, mime_type: str) -> dict[str, object]:
        from app.integrations.gemini.schema import EXTRACTION_INSTRUCTIONS, GEMINI_RESPONSE_SCHEMA

        kind = "document" if mime_type == "application/pdf" else "image"
        return self._extract(content, mime_type, kind, EXTRACTION_INSTRUCTIONS, GEMINI_RESPONSE_SCHEMA)

    def extract_meter_photo(self, content: bytes, mime_type: str) -> dict[str, object]:
        from app.integrations.gemini.meter_schema import METER_INSTRUCTIONS, METER_RESPONSE_SCHEMA

        return self._extract(content, mime_type, "image", METER_INSTRUCTIONS, METER_RESPONSE_SCHEMA)

    def _extract(
        self,
        content: bytes,
        mime_type: str,
        kind: str,
        instructions: str,
        schema: dict[str, object],
    ) -> dict[str, object]:
        if not self._settings.gemini_api_key:
            raise GeminiNotConfigured()
        encoded = b64encode(content).decode("ascii")
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=self._settings.gemini_api_key,
                http_options=types.HttpOptions(
                    timeout=self._settings.gemini_timeout_seconds * 1000
                ),
            )
            interaction = client.interactions.create(
                model=self._settings.gemini_model,
                input=[
                    {"type": "text", "text": instructions},
                    {"type": kind, "data": encoded, "mime_type": mime_type},
                ],
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": schema,
                },
                response_mime_type="application/json",
                system_instruction=instructions,
                store=False,
                timeout=self._settings.gemini_timeout_seconds,
            )
        except GeminiError:
            raise
        except Exception as exc:
            if type(exc).__name__ in {"TimeoutError", "TimeoutException", "ReadTimeout", "ConnectTimeout"}:
                raise GeminiTimeout() from exc
            logger.error("gemini_request_failed exception_type=%s", type(exc).__name__)
            raise GeminiUnavailable() from exc
        finally:
            encoded = ""
        text = getattr(interaction, "output_text", None)
        if not isinstance(text, str) or not text.strip():
            raise GeminiSchemaError()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise GeminiSchemaError() from exc
        if not isinstance(payload, dict):
            raise GeminiSchemaError()
        return payload
