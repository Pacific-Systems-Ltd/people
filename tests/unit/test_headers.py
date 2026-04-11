"""Tests for HTTP header parsing — Link, WAC-Allow, ETag."""

from people._http.headers import (
    extract_metadata,
    parse_link_headers,
    parse_wac_allow,
    resolve_acl_url,
)


class TestParseLinkHeaders:
    def test_single_link(self):
        result = parse_link_headers('<.acl>; rel="acl"')
        assert result == {"acl": ".acl"}

    def test_multiple_links(self):
        result = parse_link_headers(
            '<.acl>; rel="acl", <http://www.w3.org/ns/ldp#BasicContainer>; rel="type"'
        )
        assert result["acl"] == ".acl"
        assert result["type"] == "http://www.w3.org/ns/ldp#BasicContainer"

    def test_empty_string(self):
        assert parse_link_headers("") == {}

    def test_none_safe(self):
        assert parse_link_headers("") == {}


class TestParseWacAllow:
    def test_user_and_public(self):
        result = parse_wac_allow('user="read write", public="read"')
        assert result["user"] == {"read", "write"}
        assert result["public"] == {"read"}

    def test_user_only(self):
        result = parse_wac_allow('user="read write control"')
        assert result["user"] == {"read", "write", "control"}

    def test_empty_modes(self):
        result = parse_wac_allow('user="", public=""')
        assert result["user"] == set()

    def test_empty_string(self):
        assert parse_wac_allow("") == {}


class TestResolveAclUrl:
    def test_relative_acl(self):
        url = resolve_acl_url(
            "http://pod.example/alice/notes/hello",
            {"acl": ".acl"},
        )
        assert url == "http://pod.example/alice/notes/.acl"

    def test_absolute_acl(self):
        url = resolve_acl_url(
            "http://pod.example/alice/notes/hello",
            {"acl": "http://pod.example/alice/notes/hello.acl"},
        )
        assert url == "http://pod.example/alice/notes/hello.acl"

    def test_no_acl_link(self):
        url = resolve_acl_url("http://pod.example/resource", {})
        assert url is None

    def test_container_acl(self):
        url = resolve_acl_url(
            "http://pod.example/alice/notes/",
            {"acl": ".acl"},
        )
        assert url == "http://pod.example/alice/notes/.acl"

    def test_absolute_path_acl(self):
        url = resolve_acl_url(
            "http://pod.example/alice/notes/hello",
            {"acl": "/alice/notes/.acl"},
        )
        assert url == "http://pod.example/alice/notes/.acl"


class TestExtractMetadata:
    def test_full_headers(self):
        headers = {
            "etag": '"abc123"',
            "link": '<.acl>; rel="acl"',
            "wac-allow": 'user="read write", public="read"',
            "content-type": "text/turtle",
        }
        meta = extract_metadata(headers, "http://pod.example/resource")
        assert meta["etag"] == '"abc123"'
        assert meta["acl_url"] == "http://pod.example/.acl"
        assert meta["permissions"]["user"] == {"read", "write"}
        assert meta["content_type"] == "text/turtle"

    def test_missing_headers(self):
        meta = extract_metadata({}, "http://pod.example/resource")
        assert meta["etag"] is None
        assert meta["acl_url"] is None
        assert meta["permissions"] is None
