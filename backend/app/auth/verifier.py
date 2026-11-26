"""Token verification. Production uses Firebase Admin. Tests inject a fake verifier."""

from typing import Protocol

from app.auth.identity import (
    AuthenticatedUser,
    ExpiredIdentity,
    IdentityUnavailable,
    InvalidIdentity,
)
from app.core.config import Settings


class TokenVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedUser:
        """Return the UID from a verified token, or raise IdentityError."""

    def delete_login(self, uid: str) -> bool:
        """Delete the Auth user. False means the login is still there."""


class FakeTokenVerifier:
    """In-memory verifier for tests. The application never selects this from settings."""

    def __init__(
        self,
        tokens: dict[str, AuthenticatedUser],
        expired: set[str] | None = None,
    ) -> None:
        self._tokens = tokens
        self._expired = expired or set()
        self.deleted: set[str] = set()

    def verify(self, token: str) -> AuthenticatedUser:
        if token in self._expired:
            raise ExpiredIdentity()
        user = self._tokens.get(token)
        if user is None:
            raise InvalidIdentity()
        return user

    def delete_login(self, uid: str) -> bool:
        self.deleted.add(uid)
        return True


class FirebaseTokenVerifier:
    """Verify Firebase ID tokens with the Admin SDK. The token is not logged."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._ready = False

    def verify(self, token: str) -> AuthenticatedUser:
        self._ensure()
        from firebase_admin import auth

        try:
            decoded = auth.verify_id_token(token, check_revoked=True)
        except auth.ExpiredIdTokenError as exc:
            raise ExpiredIdentity() from exc
        except auth.RevokedIdTokenError as exc:
            raise ExpiredIdentity() from exc
        except Exception as exc:
            raise InvalidIdentity() from exc
        uid = decoded.get("uid")
        if not isinstance(uid, str) or not uid or uid != decoded.get("sub"):
            raise InvalidIdentity()
        email = decoded.get("email")
        if not isinstance(email, str):
            email = None
        return AuthenticatedUser(uid=uid, email=email)

    def delete_login(self, uid: str) -> bool:
        self._ensure()
        from firebase_admin import auth

        try:
            auth.delete_user(uid)
        except Exception as exc:
            raise IdentityUnavailable() from exc
        return True

    def _ensure(self) -> None:
        if self._ready:
            return
        try:
            _initialize(self._settings)
        except Exception as exc:
            raise IdentityUnavailable() from exc
        self._ready = True


def build_verifier(settings: Settings) -> TokenVerifier | None:
    if not settings.firebase_configured:
        return None
    return FirebaseTokenVerifier(settings)


def _initialize(settings: Settings) -> None:
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        return
    private_key = (settings.firebase_private_key or "").replace("\\n", "\n")
    certificate = credentials.Certificate(
        {
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "client_email": settings.firebase_client_email,
            "private_key": private_key,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
    options = {}
    if settings.firebase_storage_bucket:
        options["storageBucket"] = settings.firebase_storage_bucket
    firebase_admin.initialize_app(certificate, options or None)
