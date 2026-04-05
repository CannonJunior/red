"""
Tests for proposal/integrations/sharepoint.py

All HTTP calls and file I/O are mocked — no Azure/SharePoint credentials required.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

from proposal.integrations.sharepoint import (
    PROPOSAL_FOLDER_STRUCTURE,
    SharePointAPIError,
    SharePointAuthError,
    SharePointClient,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int = 200, json_body=None, text: str = "") -> MagicMock:
    """Build a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = (200 <= status_code < 300)
    resp.text = text or json.dumps(json_body or {})
    resp.json.return_value = json_body if json_body is not None else {}
    return resp


@pytest.fixture()
def tmp_token_cache(tmp_path):
    return tmp_path / "sp_token.json"


@pytest.fixture()
def client(tmp_token_cache):
    """SharePointClient pre-loaded with a fake access token."""
    c = SharePointClient(
        tenant_id="tenant-123",
        client_id="client-456",
        site_url="https://company.sharepoint.com/sites/Proposals",
        drive_name="Documents",
        token_cache_path=tmp_token_cache,
    )
    c._access_token = "fake-access-token"
    c._refresh_token = "fake-refresh-token"
    c._site_id = "site-id-001"
    c._drive_id = "drive-id-001"
    return c


# ---------------------------------------------------------------------------
# Construction & configuration
# ---------------------------------------------------------------------------

class TestSharePointClientInit:
    def test_default_drive_name(self, tmp_token_cache):
        c = SharePointClient(token_cache_path=tmp_token_cache)
        assert c.drive_name == "Documents"

    def test_site_url_trailing_slash_stripped(self, tmp_token_cache):
        c = SharePointClient(
            site_url="https://company.sharepoint.com/sites/Proposals/",
            token_cache_path=tmp_token_cache,
        )
        assert not c.site_url.endswith("/")

    def test_loads_cached_token(self, tmp_token_cache):
        tmp_token_cache.write_text(json.dumps({
            "access_token": "cached-token",
            "refresh_token": "cached-refresh",
        }))
        c = SharePointClient(token_cache_path=tmp_token_cache)
        assert c._access_token == "cached-token"

    def test_missing_token_cache_is_fine(self, tmp_path):
        c = SharePointClient(token_cache_path=tmp_path / "nonexistent.json")
        assert c._access_token is None

    def test_corrupt_token_cache_does_not_crash(self, tmp_token_cache):
        tmp_token_cache.write_text("NOT_JSON{{{")
        c = SharePointClient(token_cache_path=tmp_token_cache)
        assert c._access_token is None


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestAuthentication:
    def test_authenticate_raises_without_tenant_and_client(self, tmp_token_cache):
        c = SharePointClient(token_cache_path=tmp_token_cache)
        with pytest.raises(ValueError, match="SHAREPOINT_TENANT_ID"):
            c.authenticate()

    def test_headers_raise_when_not_authenticated(self, tmp_token_cache):
        c = SharePointClient(
            tenant_id="t", client_id="c", token_cache_path=tmp_token_cache
        )
        with pytest.raises(SharePointAuthError, match="Not authenticated"):
            c._headers()

    def test_headers_returns_bearer_token(self, client):
        headers = client._headers()
        assert headers["Authorization"] == "Bearer fake-access-token"
        assert headers["Content-Type"] == "application/json"

    def test_save_token_cache_writes_file(self, client, tmp_token_cache):
        client._save_token_cache({
            "access_token": "new-token",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        })
        data = json.loads(tmp_token_cache.read_text())
        assert data["access_token"] == "new-token"
        assert "cached_at" in data

    def test_refresh_access_token_success(self, client, tmp_token_cache):
        with patch("proposal.integrations.sharepoint.requests.post") as mock_post:
            mock_post.return_value = _mock_response(200, {
                "access_token": "refreshed",
                "refresh_token": "new-refresh",
            })
            result = client._refresh_access_token()
        assert result is True
        assert client._access_token == "refreshed"

    def test_refresh_access_token_fails_gracefully(self, client):
        with patch("proposal.integrations.sharepoint.requests.post") as mock_post:
            mock_post.return_value = _mock_response(400, {"error": "invalid_grant"})
            result = client._refresh_access_token()
        assert result is False

    def test_refresh_without_refresh_token_returns_false(self, client):
        client._refresh_token = None
        result = client._refresh_access_token()
        assert result is False


# ---------------------------------------------------------------------------
# Graph API request wrapper
# ---------------------------------------------------------------------------

class TestGraphRequest:
    def test_successful_get_returns_response(self, client):
        with patch("proposal.integrations.sharepoint.requests.request") as mock_req:
            mock_req.return_value = _mock_response(200, {"value": []})
            resp = client._graph_request("GET", "https://graph.microsoft.com/v1.0/test")
        assert resp.ok

    def test_401_triggers_token_refresh_and_retry(self, client):
        """On a 401, the client should refresh the token and retry once."""
        first = _mock_response(401)
        second = _mock_response(200, {"id": "drive-001"})
        with patch("proposal.integrations.sharepoint.requests.request") as mock_req:
            mock_req.side_effect = [first, second]
            with patch.object(client, "_refresh_access_token", return_value=True):
                resp = client._graph_request("GET", "https://graph.microsoft.com/v1.0/test")
        assert resp.status_code == 200

    def test_raises_sharepoint_api_error_on_non_2xx(self, client):
        with patch("proposal.integrations.sharepoint.requests.request") as mock_req:
            mock_req.return_value = _mock_response(
                403, {"error": {"message": "Access denied"}}
            )
            with pytest.raises(SharePointAPIError) as exc_info:
                client._graph_request("GET", "https://graph.microsoft.com/v1.0/test")
        assert exc_info.value.status_code == 403

    def test_api_error_message_extracted_from_graph_envelope(self, client):
        with patch("proposal.integrations.sharepoint.requests.request") as mock_req:
            mock_req.return_value = _mock_response(
                500, {"error": {"message": "Internal server error"}}
            )
            with pytest.raises(SharePointAPIError, match="Internal server error"):
                client._graph_request("GET", "https://graph.microsoft.com/v1.0/test")


# ---------------------------------------------------------------------------
# Site / Drive resolution
# ---------------------------------------------------------------------------

class TestSiteDriveResolution:
    def test_get_site_id_returns_cached(self, client):
        """Should not make a request when _site_id is already set."""
        with patch.object(client, "_graph_request") as mock_req:
            result = client._get_site_id()
        assert result == "site-id-001"
        mock_req.assert_not_called()

    def test_get_drive_id_returns_cached(self, client):
        with patch.object(client, "_graph_request") as mock_req:
            result = client._get_drive_id()
        assert result == "drive-id-001"
        mock_req.assert_not_called()

    def test_get_drive_id_falls_back_to_default_drive(self, client):
        """When named drive not found, falls back to default drive."""
        client._drive_id = None
        drives_resp = _mock_response(200, {"value": [{"name": "Other", "id": "other-drive"}]})
        default_drive_resp = _mock_response(200, {"id": "default-drive-id"})
        with patch.object(client, "_graph_request", side_effect=[drives_resp, default_drive_resp]):
            drive_id = client._get_drive_id()
        assert drive_id == "default-drive-id"

    def test_get_drive_id_finds_named_drive(self, client):
        client._drive_id = None
        drives_resp = _mock_response(200, {
            "value": [
                {"name": "Other", "id": "other-id"},
                {"name": "Documents", "id": "docs-drive-id"},
            ]
        })
        with patch.object(client, "_graph_request", return_value=drives_resp):
            drive_id = client._get_drive_id()
        assert drive_id == "docs-drive-id"


# ---------------------------------------------------------------------------
# Folder operations
# ---------------------------------------------------------------------------

class TestFolderOperations:
    def test_create_folder_posts_correct_payload(self, client):
        resp = _mock_response(201, {"id": "new-folder-id", "webUrl": "https://sp/folder"})
        with patch.object(client, "_graph_request", return_value=resp) as mock_req:
            result = client._create_folder("parent-id", "MyFolder")
        assert result["id"] == "new-folder-id"
        call_json = mock_req.call_args.kwargs["json"]
        assert call_json["name"] == "MyFolder"
        assert "folder" in call_json

    def test_create_nested_folders_builds_hierarchy(self, client):
        """_create_nested_folders should call _create_folder once per unique path segment."""
        call_count = {"n": 0}
        def fake_create(parent_id, name):
            call_count["n"] += 1
            return {"id": f"folder-{call_count['n']}"}

        with patch.object(client, "_create_folder", side_effect=fake_create):
            client._create_nested_folders("root-id", [
                "A/B",
                "A/C",
                "D",
            ])
        # Segments: A, A/B, A/C, D = 4 unique paths (A counted once due to cache)
        assert call_count["n"] == 4

    def test_create_proposal_folder_returns_url_and_id(self, client):
        folder_resp = {"id": "prop-folder-id", "webUrl": "https://sp/Proposals/FY26/AFRL"}
        root_resp   = {"id": "root-id"}

        seq = [
            _mock_response(200, root_resp),   # _get_root_id
            _mock_response(201, {"id": "proposals-id"}),  # Proposals folder
            _mock_response(201, {"id": "fy-id"}),         # FY26 folder
            _mock_response(201, folder_resp),             # proposal folder
        ]

        def patched_graph(method, url, **kw):
            return seq.pop(0)

        def patched_create(parent_id, name):
            if name == "AFRL_FA8612-26-R-0001_Widget System":
                return folder_resp
            return {"id": f"folder-{name}"}

        with patch.object(client, "_graph_request", side_effect=patched_graph), \
             patch.object(client, "_create_folder", side_effect=patched_create), \
             patch.object(client, "_create_nested_folders"):
            url, item_id = client.create_proposal_folder(
                solicitation_number="FA8612-26-R-0001",
                agency="AFRL",
                title="Widget System",
                fiscal_year="FY26",
            )
        assert url == "https://sp/Proposals/FY26/AFRL"
        assert item_id == "prop-folder-id"

    def test_create_proposal_folder_sanitizes_special_chars(self, client):
        """Slashes and colons in title/agency should be replaced in folder name."""
        created_names = []
        def fake_create(parent_id, name):
            created_names.append(name)
            return {"id": f"id-{name}", "webUrl": f"https://sp/{name}"}

        with patch.object(client, "_get_root_id", return_value="root"), \
             patch.object(client, "_create_folder", side_effect=fake_create), \
             patch.object(client, "_create_nested_folders"):
            client.create_proposal_folder(
                solicitation_number="FA/8612",
                agency="Air Force",
                title="Widget: System",
                fiscal_year="FY26",
            )
        # Find the proposal folder name (last non-FY folder created at top level)
        prop_folder = created_names[-1]
        assert "/" not in prop_folder
        assert ":" not in prop_folder

    def test_proposal_folder_structure_has_expected_subfolders(self):
        """PROPOSAL_FOLDER_STRUCTURE should include required volume paths."""
        assert "00_RFP" in PROPOSAL_FOLDER_STRUCTURE
        assert any("Vol-1-Technical" in p for p in PROPOSAL_FOLDER_STRUCTURE)
        assert any("Vol-3-Cost" in p for p in PROPOSAL_FOLDER_STRUCTURE)
        assert any("Red-Team" in p for p in PROPOSAL_FOLDER_STRUCTURE)


# ---------------------------------------------------------------------------
# Document upload
# ---------------------------------------------------------------------------

class TestDocumentUpload:
    def test_upload_small_file(self, client, tmp_path):
        """Files ≤ 4MB should use a simple PUT."""
        test_file = tmp_path / "test.docx"
        test_file.write_bytes(b"small content")

        upload_resp = {"id": "file-id-001", "webUrl": "https://sp/file.docx"}
        with patch.object(client, "_graph_request", return_value=_mock_response(200, upload_resp)):
            result = client.upload_document("folder-id", test_file)
        assert result["id"] == "file-id-001"

    def test_upload_uses_custom_file_name(self, client, tmp_path):
        """file_name override should be used in the Graph API URL."""
        test_file = tmp_path / "local_name.docx"
        test_file.write_bytes(b"content")

        called_url = {}
        def capture_request(method, url, **kw):
            called_url["url"] = url
            return _mock_response(200, {"id": "x"})

        with patch.object(client, "_graph_request", side_effect=capture_request):
            client.upload_document("folder-id", test_file, file_name="custom_name.docx")
        assert "custom_name.docx" in called_url["url"]

    def test_upload_large_file_uses_session(self, client, tmp_path):
        """Files > 4MB should use the upload session path."""
        large_file = tmp_path / "large.docx"
        large_file.write_bytes(b"x" * (5 * 1024 * 1024))

        with patch.object(client, "_upload_large_file", return_value={"status": "uploaded"}) as mock_large:
            client.upload_document("folder-id", large_file)
        mock_large.assert_called_once()


# ---------------------------------------------------------------------------
# Sharing links
# ---------------------------------------------------------------------------

class TestSharingLinks:
    def test_create_sharing_link_returns_url(self, client):
        link_resp = {"link": {"webUrl": "https://sp/share/abc123"}}
        with patch.object(client, "_graph_request", return_value=_mock_response(200, link_resp)):
            url = client.create_sharing_link("item-id-001")
        assert url == "https://sp/share/abc123"

    def test_create_sharing_link_posts_correct_payload(self, client):
        link_resp = {"link": {"webUrl": "https://sp/edit-link"}}
        captured = {}

        def capture(method, url, **kw):
            captured["json"] = kw.get("json", {})
            return _mock_response(200, link_resp)

        with patch.object(client, "_graph_request", side_effect=capture):
            client.create_sharing_link("item-id", link_type="edit", scope="organization")
        assert captured["json"]["type"] == "edit"
        assert captured["json"]["scope"] == "organization"

    def test_create_sharing_link_missing_returns_empty_string(self, client):
        with patch.object(client, "_graph_request", return_value=_mock_response(200, {})):
            url = client.create_sharing_link("item-id")
        assert url == ""
