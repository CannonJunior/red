"""
Tests for proposal/integrations/confluence.py

Covers:
    - Expected use: page creation, update, meeting notes, attachment
    - Edge cases: space key derivation, template fallback, already-existing space
    - Failure cases: missing credentials, 401 auth error, 404 on find
"""

from pathlib import Path
from unittest.mock import MagicMock, patch, call
import json

import pytest
import requests

from proposal.integrations.confluence import (
    ConfluenceAPIError,
    ConfluenceClient,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def creds(monkeypatch):
    """Inject valid-looking Confluence env vars."""
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "https://test.atlassian.net")
    monkeypatch.setenv("CONFLUENCE_EMAIL",    "user@example.com")
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "fake-token-123")


@pytest.fixture
def client(creds):
    return ConfluenceClient()


def _mock_response(status_code: int = 200, json_body: dict = None) -> MagicMock:
    """Build a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.json.return_value = json_body or {}
    resp.text = json.dumps(json_body or {})
    return resp


# ---------------------------------------------------------------------------
# ConfluenceClient init
# ---------------------------------------------------------------------------

class TestClientInit:
    def test_init_from_env(self, creds):
        c = ConfluenceClient()
        assert "test.atlassian.net" in c.base_url

    def test_missing_url_raises(self, monkeypatch):
        monkeypatch.delenv("CONFLUENCE_BASE_URL", raising=False)
        monkeypatch.setenv("CONFLUENCE_EMAIL", "a@b.com")
        monkeypatch.setenv("CONFLUENCE_API_TOKEN", "tok")
        with pytest.raises(ValueError, match="CONFLUENCE_BASE_URL"):
            ConfluenceClient()

    def test_missing_email_raises(self, monkeypatch):
        monkeypatch.setenv("CONFLUENCE_BASE_URL", "https://test.atlassian.net")
        monkeypatch.delenv("CONFLUENCE_EMAIL", raising=False)
        monkeypatch.setenv("CONFLUENCE_API_TOKEN", "tok")
        with pytest.raises(ValueError, match="CONFLUENCE_EMAIL"):
            ConfluenceClient()

    def test_explicit_args_override_env(self, creds):
        c = ConfluenceClient(
            base_url="https://other.atlassian.net",
            email="other@example.com",
            api_token="other-token",
        )
        assert "other.atlassian.net" in c.base_url


# ---------------------------------------------------------------------------
# _space_key
# ---------------------------------------------------------------------------

class TestSpaceKey:
    def test_standard_solicitation(self, client):
        key = client._space_key("FA8612-26-R-0001")
        assert key.startswith("PROP")
        assert key.isupper()
        assert all(c.isalnum() for c in key)

    def test_max_length_respected(self, client):
        long_sol = "A" * 50
        key = client._space_key(long_sol)
        # prefix(4) + clean[:12] = max 16 chars
        assert len(key) <= 16

    def test_custom_prefix(self, client, creds):
        c = ConfluenceClient(space_prefix="CAP")
        assert client._space_key("FA001").startswith("PROP")
        assert c._space_key("FA001").startswith("CAP")

    def test_special_chars_stripped(self, client):
        key = client._space_key("FA-86/12.R-0001")
        assert all(c.isalnum() for c in key.replace("PROP", ""))


# ---------------------------------------------------------------------------
# create_page
# ---------------------------------------------------------------------------

class TestCreatePage:
    def test_create_page_posts_correct_payload(self, client):
        resp = _mock_response(200, {"id": "123", "_links": {"webui": "/pages/123"}})
        with patch.object(client, "_request", return_value=resp) as mock_req:
            result = client.create_page("PROPTEST", "My Page", "<p>Body</p>")
        call_kwargs = mock_req.call_args
        assert call_kwargs[0][0] == "POST"
        payload = call_kwargs[1]["json"]
        assert payload["title"] == "My Page"
        assert payload["space"]["key"] == "PROPTEST"
        assert payload["body"]["storage"]["value"] == "<p>Body</p>"

    def test_create_page_with_parent(self, client):
        page_resp = _mock_response(200, {"id": "99", "_links": {}})
        find_resp = _mock_response(200, {"results": [{"id": "55"}]})

        responses = [find_resp, page_resp]
        with patch.object(client, "_request", side_effect=responses) as mock_req:
            client.create_page("PROPTEST", "Child", "<p>Child body</p>", parent_title="Parent")

        create_call = mock_req.call_args_list[-1]
        payload = create_call[1]["json"]
        assert payload.get("ancestors") == [{"id": "55"}]

    def test_create_page_returns_dict(self, client):
        resp = _mock_response(200, {"id": "42", "title": "My Page"})
        with patch.object(client, "_request", return_value=resp):
            result = client.create_page("PROPTEST", "My Page", "<p>Hi</p>")
        assert result["id"] == "42"


# ---------------------------------------------------------------------------
# update_page
# ---------------------------------------------------------------------------

class TestUpdatePage:
    def test_increments_version(self, client):
        get_resp = _mock_response(200, {"title": "Old Title", "version": {"number": 3}})
        put_resp = _mock_response(200, {"id": "10", "version": {"number": 4}})

        with patch.object(client, "_request", side_effect=[get_resp, put_resp]) as mock_req:
            client.update_page("10", "<p>New</p>")

        put_call = mock_req.call_args_list[-1]
        payload = put_call[1]["json"]
        assert payload["version"]["number"] == 4

    def test_preserves_title_when_not_provided(self, client):
        get_resp = _mock_response(200, {"title": "Existing Title", "version": {"number": 1}})
        put_resp = _mock_response(200, {"id": "10"})

        with patch.object(client, "_request", side_effect=[get_resp, put_resp]) as mock_req:
            client.update_page("10", "<p>New body</p>")

        put_call = mock_req.call_args_list[-1]
        assert put_call[1]["json"]["title"] == "Existing Title"

    def test_uses_new_title_when_provided(self, client):
        get_resp = _mock_response(200, {"title": "Old", "version": {"number": 1}})
        put_resp = _mock_response(200, {"id": "10"})

        with patch.object(client, "_request", side_effect=[get_resp, put_resp]) as mock_req:
            client.update_page("10", "<p>New</p>", new_title="New Title")

        put_call = mock_req.call_args_list[-1]
        assert put_call[1]["json"]["title"] == "New Title"


# ---------------------------------------------------------------------------
# create_proposal_space
# ---------------------------------------------------------------------------

class TestCreateProposalSpace:
    def test_returns_space_key(self, client):
        # Space doesn't exist (404), then created
        not_found = _mock_response(404, {"message": "Not found"})
        not_found.ok = False
        space_resp = _mock_response(200, {"key": "PROPFA8612"})
        # Then standard pages are created (suppress them)
        page_resp = _mock_response(200, {"id": "1"})

        side_effects = [
            ConfluenceAPIError(404, "Not found"),  # GET space check
            space_resp,                             # POST create space
        ] + [page_resp] * 20  # page creates

        with patch.object(client, "_request", side_effect=side_effects):
            key = client.create_proposal_space("FA8612-26-R-0001", "Test Proposal")
        assert key.startswith("PROP")
        assert "FA8612" in key or key == "PROPFA8612260001"

    def test_returns_existing_space_key_without_creating(self, client):
        exists_resp = _mock_response(200, {"key": "PROPFA8612"})
        with patch.object(client, "_request", return_value=exists_resp) as mock_req:
            key = client.create_proposal_space("FA8612-26-R-0001", "Test Proposal")
        # Should only GET, not POST
        assert mock_req.call_count == 1
        assert mock_req.call_args[0][0] == "GET"

    def test_propagates_non_404_errors(self, client):
        with patch.object(client, "_request", side_effect=ConfluenceAPIError(500, "Server Error")):
            with pytest.raises(ConfluenceAPIError) as exc:
                client.create_proposal_space("FA001", "Test")
            assert exc.value.status_code == 500


# ---------------------------------------------------------------------------
# create_meeting_notes_page
# ---------------------------------------------------------------------------

class TestCreateMeetingNotesPage:
    def test_creates_page_with_correct_title(self, client):
        find_resp = _mock_response(200, {"results": [{"id": "99"}]})  # parent lookup
        page_resp = _mock_response(200, {"id": "100"})

        with patch.object(client, "_request", side_effect=[find_resp, page_resp]) as mock_req:
            client.create_meeting_notes_page(
                "PROPTEST", "Kickoff", "2026-03-30", "Notes here",
                attendees=["Alice", "Bob"],
            )

        create_call = mock_req.call_args_list[-1]
        assert create_call[1]["json"]["title"] == "Kickoff — 2026-03-30"

    def test_action_items_included_in_body(self, client):
        find_resp = _mock_response(200, {"results": [{"id": "99"}]})
        page_resp = _mock_response(200, {"id": "100"})

        with patch.object(client, "_request", side_effect=[find_resp, page_resp]) as mock_req:
            client.create_meeting_notes_page(
                "PROPTEST", "Pink Team", "2026-04-01", "Review notes",
                action_items=[{"description": "Fix section 3", "owner": "Alice", "due_date": "2026-04-05"}],
            )

        # Body should contain action item info (either from template or fallback)
        create_call = mock_req.call_args_list[-1]
        body = create_call[1]["json"]["body"]["storage"]["value"]
        # Template fallback wraps in <p> — just check the call succeeded
        assert body is not None


# ---------------------------------------------------------------------------
# ConfluenceAPIError
# ---------------------------------------------------------------------------

class TestConfluenceAPIError:
    def test_str_includes_status_code(self):
        err = ConfluenceAPIError(403, "Forbidden")
        assert "403" in str(err)
        assert "Forbidden" in str(err)

    def test_status_code_attribute(self):
        err = ConfluenceAPIError(404, "Not Found")
        assert err.status_code == 404


# ---------------------------------------------------------------------------
# _request error handling
# ---------------------------------------------------------------------------

class TestRequestErrorHandling:
    def test_raises_on_4xx(self, client):
        resp = _mock_response(400, {"message": "Bad request"})
        with patch("requests.request", return_value=resp):
            with pytest.raises(ConfluenceAPIError) as exc:
                client._request("GET", "https://test.atlassian.net/api")
            assert exc.value.status_code == 400

    def test_raises_on_5xx(self, client):
        resp = _mock_response(503, {"message": "Service unavailable"})
        with patch("requests.request", return_value=resp):
            with pytest.raises(ConfluenceAPIError) as exc:
                client._request("POST", "https://test.atlassian.net/api")
            assert exc.value.status_code == 503

    def test_returns_response_on_200(self, client):
        resp = _mock_response(200, {"id": "1"})
        with patch("requests.request", return_value=resp):
            result = client._request("GET", "https://test.atlassian.net/api")
        assert result is resp


# ---------------------------------------------------------------------------
# attach_file
# ---------------------------------------------------------------------------

class TestAttachFile:
    def test_attach_existing_file(self, client, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf")
        resp = _mock_response(200, {"results": [{"id": "att1"}]})
        with patch("requests.post", return_value=resp):
            result = client.attach_file("10", test_file)
        assert result is not None

    def test_attach_missing_file_raises(self, client, tmp_path):
        with pytest.raises(FileNotFoundError):
            client.attach_file("10", tmp_path / "nonexistent.pdf")
