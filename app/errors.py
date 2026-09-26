"""User-facing errors. Each carries a safe message and the HTTP status it maps to."""


class LegalLensError(Exception):
    """Base error whose message is safe to show to the user."""

    status_code = 500

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class PdfValidationError(LegalLensError):
    """The upload is not a readable, supported PDF within the limits."""

    status_code = 400


class UnsupportedDocumentError(LegalLensError):
    """The document does not appear to be an employment document."""

    status_code = 422


class LLMServiceError(LegalLensError):
    """The AI service failed, was busy, or returned an unusable response."""

    status_code = 502


class RateLimitExceededError(LegalLensError):
    """Too many brief requests from one client."""

    status_code = 429


class SampleUnavailableError(LegalLensError):
    """The bundled sample brief is missing or invalid."""

    status_code = 503
