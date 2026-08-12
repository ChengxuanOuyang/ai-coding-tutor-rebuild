class DomainError(Exception):
    """An expected domain failure that is safe to expose at an API boundary."""

    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class AuthenticationError(DomainError):
    """Authentication failed without revealing credential details."""


class ConflictError(DomainError):
    """A requested state conflicts with an existing domain resource."""


class NotFoundError(DomainError):
    """A requested domain resource is unavailable to the caller."""


class UpstreamInvalidResponseError(DomainError):
    """An upstream provider returned a response outside its contract."""


class UpstreamUnavailableError(DomainError):
    """An upstream provider could not complete a request."""
