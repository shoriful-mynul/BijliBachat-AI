"""Failures from Gemini. Messages stay generic so a bill is not logged."""


class GeminiError(Exception):
    """Base error. Subclasses carry no document text."""


class GeminiNotConfigured(GeminiError):
    """No server-side API key is configured."""


class GeminiUnavailable(GeminiError):
    """The extraction service could not be used."""


class GeminiTimeout(GeminiError):
    """The extraction service did not answer in time."""


class GeminiSchemaError(GeminiError):
    """The model response was not the extraction schema."""
