"""Tests for ACP vs WAC detection (SP-23)."""


from pacific_solid._acl.acp import AuthSchemeError, detect_auth_scheme


class TestDetectAuthScheme:
    def test_wac_detected_from_acl_rel(self):
        assert detect_auth_scheme({"acl": ".acl"}) == "wac"

    def test_acp_detected_from_acp_rel(self):
        assert detect_auth_scheme({
            "http://www.w3.org/ns/solid/acp#accessControl": "/acp/resource",
        }) == "acp"

    def test_unknown_when_no_auth_headers(self):
        assert detect_auth_scheme({}) == "unknown"

    def test_unknown_when_only_type_headers(self):
        assert detect_auth_scheme({"type": "http://www.w3.org/ns/ldp#Container"}) == "unknown"

    def test_wac_takes_precedence_when_both_present(self):
        """Edge case: server advertises both. WAC detected first."""
        headers = {
            "acl": ".acl",
            "http://www.w3.org/ns/solid/acp#accessControl": "/acp/resource",
        }
        assert detect_auth_scheme(headers) == "wac"


class TestAuthSchemeError:
    def test_error_message(self):
        err = AuthSchemeError("http://pod/resource")
        assert "ACP" in str(err)
        assert "WAC" in str(err)
        assert err.url == "http://pod/resource"

    def test_inherits_from_solid_error(self):
        from pacific_solid._http.errors import SolidError
        err = AuthSchemeError("http://pod/resource")
        assert isinstance(err, SolidError)
