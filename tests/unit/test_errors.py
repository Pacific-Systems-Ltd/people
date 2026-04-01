"""Tests for the Solid error hierarchy."""

import pytest
from people import (
    SolidError,
    AuthenticationError,
    AccessDeniedError,
    NotFoundError,
    ConflictError,
    PreconditionFailedError,
    PatchError,
)
from people._http.errors import raise_for_status


class TestErrorHierarchy:
    def test_all_inherit_from_solid_error(self):
        assert issubclass(AuthenticationError, SolidError)
        assert issubclass(AccessDeniedError, SolidError)
        assert issubclass(NotFoundError, SolidError)
        assert issubclass(ConflictError, SolidError)
        assert issubclass(PreconditionFailedError, SolidError)
        assert issubclass(PatchError, SolidError)

    def test_not_builtin_permission_error(self):
        """AccessDeniedError must NOT be PermissionError (avoids Python builtin)."""
        assert not issubclass(AccessDeniedError, PermissionError)

    def test_error_has_status_code(self):
        err = SolidError("test", status_code=401, url="http://example.org")
        assert err.status_code == 401
        assert err.url == "http://example.org"


class TestRaiseForStatus:
    def test_200_no_error(self):
        raise_for_status(200, "http://example.org")

    def test_401_raises_auth_error(self):
        with pytest.raises(AuthenticationError) as exc_info:
            raise_for_status(401, "http://example.org")
        assert exc_info.value.status_code == 401

    def test_403_raises_access_denied(self):
        with pytest.raises(AccessDeniedError):
            raise_for_status(403, "http://example.org")

    def test_404_raises_not_found(self):
        with pytest.raises(NotFoundError):
            raise_for_status(404, "http://example.org")

    def test_409_raises_conflict(self):
        with pytest.raises(ConflictError):
            raise_for_status(409, "http://example.org")

    def test_412_raises_precondition_failed(self):
        with pytest.raises(PreconditionFailedError):
            raise_for_status(412, "http://example.org")

    def test_422_raises_patch_error(self):
        with pytest.raises(PatchError):
            raise_for_status(422, "http://example.org")

    def test_500_raises_generic_solid_error(self):
        with pytest.raises(SolidError):
            raise_for_status(500, "http://example.org")

    def test_error_includes_body(self):
        with pytest.raises(SolidError) as exc_info:
            raise_for_status(500, "http://example.org", "Internal server error details")
        assert "Internal server error details" in str(exc_info.value)
