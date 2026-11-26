"""Identity taken from a verified Firebase token. A request body is not a source of UID."""

from dataclasses import dataclass


class IdentityError(Exception):
    """Safe authentication failure. The message is fixed and never includes a token."""


class InvalidIdentity(IdentityError):
    pass


class ExpiredIdentity(IdentityError):
    pass


class IdentityUnavailable(IdentityError):
    pass


@dataclass(frozen=True)
class AuthenticatedUser:
    uid: str
    email: str | None = None
