"""
SharePoint Integration Client — Microsoft Graph API.

Creates and manages proposal folder structures in SharePoint document libraries.
Uses OAuth2 device code flow (no web server required) with token caching.

Configuration (all via environment variables):
    SHAREPOINT_TENANT_ID    — Azure AD tenant ID
    SHAREPOINT_CLIENT_ID    — App registration client ID
    SHAREPOINT_SITE_URL     — SharePoint site URL (e.g., https://company.sharepoint.com/sites/Proposals)
    SHAREPOINT_DRIVE_NAME   — Document library name (default: "Documents")
    SHAREPOINT_TOKEN_CACHE  — Token cache file path (default: ~/.red/sharepoint_token.json)

Setup:
    1. Register an app in Azure AD (no secret needed for device code flow)
    2. Grant delegated permissions: Sites.ReadWrite.All, Files.ReadWrite.All
    3. Run client.authenticate() once to complete device code flow
    4. Token is cached and refreshed automatically thereafter
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
AUTHORITY_BASE = "https://login.microsoftonline.com"
SCOPE = "https://graph.microsoft.com/.default offline_access"

# Standard proposal folder structure (path segments relative to root)
PROPOSAL_FOLDER_STRUCTURE = [
    "00_RFP",
    "01_Analysis",
    "02_BidNoBid",
    "03_Working/Vol-1-Technical",
    "03_Working/Vol-2-Management",
    "03_Working/Vol-3-Cost",
    "03_Working/Vol-4-PastPerformance",
    "04_Reviews/Pink-Team",
    "04_Reviews/Red-Team",
    "04_Reviews/Gold-Team",
    "05_Final/Internal",
    "05_Final/Submission",
]


class SharePointAuthError(Exception):
    """Raised when SharePoint authentication fails."""
    pass


class SharePointAPIError(Exception):
    """Raised on non-2xx Microsoft Graph API responses."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Graph API error {status_code}: {message}")


class SharePointClient:
    """
    Microsoft Graph API client for SharePoint document library management.

    Uses MSAL device code flow for authentication. The first call to
    authenticate() will print a URL and code for the user to complete
    in a browser. Subsequent calls use the cached refresh token.

    Example:
        client = SharePointClient()
        client.authenticate()  # One-time browser step
        folder_url = client.create_proposal_folder("FA8612-26-R-0001", "AFRL", "My Effort")
    """

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        site_url: Optional[str] = None,
        drive_name: Optional[str] = None,
        token_cache_path: Optional[Path] = None,
    ):
        """
        Initialize SharePoint client from environment variables.

        Args:
            tenant_id: Override SHAREPOINT_TENANT_ID.
            client_id: Override SHAREPOINT_CLIENT_ID.
            site_url: Override SHAREPOINT_SITE_URL.
            drive_name: Override SHAREPOINT_DRIVE_NAME.
            token_cache_path: Override token cache file location.
        """
        self.tenant_id = tenant_id or os.getenv("SHAREPOINT_TENANT_ID", "")
        self.client_id = client_id or os.getenv("SHAREPOINT_CLIENT_ID", "")
        self.site_url = (site_url or os.getenv("SHAREPOINT_SITE_URL", "")).rstrip("/")
        self.drive_name = drive_name or os.getenv("SHAREPOINT_DRIVE_NAME", "Documents")

        default_cache = Path.home() / ".red" / "sharepoint_token.json"
        self.token_cache_path = token_cache_path or Path(
            os.getenv("SHAREPOINT_TOKEN_CACHE", str(default_cache))
        )

        self._access_token: Optional[str] = None
        self._site_id: Optional[str] = None
        self._drive_id: Optional[str] = None

        # Load cached token if available
        self._load_cached_token()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _load_cached_token(self) -> None:
        """Load access and refresh tokens from cache file."""
        if self.token_cache_path.exists():
            try:
                with open(self.token_cache_path) as f:
                    cache = json.load(f)
                self._access_token = cache.get("access_token")
                self._refresh_token = cache.get("refresh_token")
                logger.debug("Loaded SharePoint token from cache")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Could not load token cache: %s", e)

    def _save_token_cache(self, token_response: Dict[str, Any]) -> None:
        """Save tokens to cache file."""
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_cache_path, "w") as f:
            json.dump({
                "access_token": token_response.get("access_token"),
                "refresh_token": token_response.get("refresh_token"),
                "expires_in": token_response.get("expires_in"),
                "cached_at": datetime.now().isoformat(),
            }, f, indent=2)

    def authenticate(self) -> None:
        """
        Perform OAuth2 device code flow authentication.

        Prints a URL and code for the user to enter in a browser.
        Token is cached after successful authentication.

        Raises:
            SharePointAuthError: If authentication fails.
            ValueError: If tenant_id or client_id not configured.
        """
        if not self.tenant_id or not self.client_id:
            raise ValueError(
                "SHAREPOINT_TENANT_ID and SHAREPOINT_CLIENT_ID must be set. "
                "See PLANNING.md Section 6.2 for setup instructions."
            )

        # Step 1: Request device code
        device_url = f"{AUTHORITY_BASE}/{self.tenant_id}/oauth2/v2.0/devicecode"
        resp = requests.post(device_url, data={
            "client_id": self.client_id,
            "scope": SCOPE,
        }, timeout=30)
        resp.raise_for_status()
        device_data = resp.json()

        print(f"\n{'='*60}")
        print("SharePoint Authentication Required")
        print(f"{'='*60}")
        print(f"1. Open: {device_data['verification_uri']}")
        print(f"2. Enter code: {device_data['user_code']}")
        print("3. Sign in with your Microsoft account")
        print(f"{'='*60}\n")

        # Step 2: Poll for token
        token_url = f"{AUTHORITY_BASE}/{self.tenant_id}/oauth2/v2.0/token"
        import time
        interval = device_data.get("interval", 5)
        deadline = time.time() + device_data.get("expires_in", 900)

        while time.time() < deadline:
            time.sleep(interval)
            token_resp = requests.post(token_url, data={
                "client_id": self.client_id,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_data["device_code"],
            }, timeout=30)
            token_data = token_resp.json()

            if "access_token" in token_data:
                self._access_token = token_data["access_token"]
                self._save_token_cache(token_data)
                logger.info("SharePoint authentication successful")
                print("Authentication successful! Token cached.")
                return
            elif token_data.get("error") == "authorization_pending":
                continue
            else:
                raise SharePointAuthError(
                    f"Authentication failed: {token_data.get('error_description', token_data)}"
                )

        raise SharePointAuthError("Device code authentication timed out")

    def _refresh_access_token(self) -> bool:
        """Attempt to refresh the access token using the cached refresh token."""
        refresh_token = getattr(self, "_refresh_token", None)
        if not refresh_token:
            return False
        token_url = f"{AUTHORITY_BASE}/{self.tenant_id}/oauth2/v2.0/token"
        resp = requests.post(token_url, data={
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": SCOPE,
        }, timeout=30)
        if resp.ok:
            token_data = resp.json()
            self._access_token = token_data.get("access_token")
            self._save_token_cache(token_data)
            return True
        return False

    def _headers(self) -> Dict[str, str]:
        """Return auth headers for Graph API calls."""
        if not self._access_token:
            raise SharePointAuthError(
                "Not authenticated. Call client.authenticate() first."
            )
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def _graph_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Execute a Graph API request with automatic token refresh.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE).
            url: Full Graph API URL.
            **kwargs: Additional requests arguments.

        Returns:
            requests.Response: The response object.

        Raises:
            SharePointAPIError: On non-2xx response after retry.
        """
        resp = requests.request(method, url, headers=self._headers(), **kwargs)
        if resp.status_code == 401:
            # Reason: Token may have expired — attempt refresh before failing
            if self._refresh_access_token():
                resp = requests.request(method, url, headers=self._headers(), **kwargs)
        if not resp.ok:
            try:
                detail = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                detail = resp.text
            raise SharePointAPIError(resp.status_code, detail)
        return resp

    # ------------------------------------------------------------------
    # Site and Drive resolution
    # ------------------------------------------------------------------

    def _get_site_id(self) -> str:
        """Resolve the SharePoint site ID from the configured site URL."""
        if self._site_id:
            return self._site_id
        # Extract hostname and site path for Graph API
        from urllib.parse import urlparse
        parsed = urlparse(self.site_url)
        host = parsed.netloc
        site_path = parsed.path.lstrip("/")
        resp = self._graph_request(
            "GET",
            f"{GRAPH_BASE}/sites/{host}:/{site_path}",
            timeout=15,
        )
        self._site_id = resp.json()["id"]
        return self._site_id

    def _get_drive_id(self) -> str:
        """Resolve the document library drive ID."""
        if self._drive_id:
            return self._drive_id
        site_id = self._get_site_id()
        resp = self._graph_request(
            "GET",
            f"{GRAPH_BASE}/sites/{site_id}/drives",
            timeout=15,
        )
        drives = resp.json().get("value", [])
        for drive in drives:
            if drive.get("name") == self.drive_name:
                self._drive_id = drive["id"]
                return self._drive_id
        # Fallback: use default drive
        resp = self._graph_request(
            "GET",
            f"{GRAPH_BASE}/sites/{site_id}/drive",
            timeout=15,
        )
        self._drive_id = resp.json()["id"]
        return self._drive_id

    # ------------------------------------------------------------------
    # Folder operations
    # ------------------------------------------------------------------

    def _create_folder(self, parent_id: str, folder_name: str) -> Dict[str, Any]:
        """
        Create a single folder under a parent item.

        Args:
            parent_id: Parent folder/root item ID.
            folder_name: Name for the new folder.

        Returns:
            Dict: Created folder metadata (id, webUrl, etc.).
        """
        site_id = self._get_site_id()
        drive_id = self._get_drive_id()
        resp = self._graph_request(
            "POST",
            f"{GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/items/{parent_id}/children",
            json={
                "name": folder_name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "rename",
            },
            timeout=30,
        )
        return resp.json()

    def _get_root_id(self) -> str:
        """Get the root drive item ID."""
        site_id = self._get_site_id()
        drive_id = self._get_drive_id()
        resp = self._graph_request(
            "GET",
            f"{GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/root",
            timeout=15,
        )
        return resp.json()["id"]

    def create_proposal_folder(
        self,
        solicitation_number: str,
        agency: str,
        title: str,
        fiscal_year: str = "",
    ) -> Tuple[str, str]:
        """
        Create the standard proposal folder structure in SharePoint.

        Folder path: Proposals/{FY}/{Agency}_{SolicitationNumber}_{ShortTitle}/

        Args:
            solicitation_number: Solicitation number (e.g., FA8612-26-R-0001).
            agency: Agency short name (e.g., AFRL).
            title: Proposal title (truncated to 50 chars for path safety).
            fiscal_year: Fiscal year string (e.g., FY26). Auto-derived if empty.

        Returns:
            Tuple[str, str]: (folder_url, sharepoint_item_id)
        """
        from datetime import datetime

        if not fiscal_year:
            now = datetime.now()
            fy = now.year + 1 if now.month >= 10 else now.year
            fiscal_year = f"FY{str(fy)[2:]}"

        # Sanitize components for SharePoint path (no special chars)
        safe_sol = solicitation_number.replace("/", "-").replace(" ", "_")
        safe_agency = agency.replace("/", "-").replace(" ", "_")
        safe_title = title[:50].replace("/", "-").replace("\\", "").replace(":", "").strip()
        proposal_folder_name = f"{safe_agency}_{safe_sol}_{safe_title}"

        root_id = self._get_root_id()
        site_id = self._get_site_id()
        drive_id = self._get_drive_id()

        # Ensure Proposals/{FY}/ parent exists
        proposals_folder = self._create_folder(root_id, "Proposals")
        fy_folder = self._create_folder(proposals_folder["id"], fiscal_year)
        proposal_folder = self._create_folder(fy_folder["id"], proposal_folder_name)

        # Create all standard sub-folders
        self._create_nested_folders(proposal_folder["id"], PROPOSAL_FOLDER_STRUCTURE)

        folder_url = proposal_folder.get("webUrl", "")
        folder_id = proposal_folder.get("id", "")
        logger.info("Created SharePoint proposal folder: %s", folder_url)
        return folder_url, folder_id

    def _create_nested_folders(self, parent_id: str, paths: List[str]) -> None:
        """
        Create nested folders from a list of path strings.

        Args:
            parent_id: Root parent item ID.
            paths: List of path strings (e.g., "03_Working/Vol-1-Technical").
        """
        folder_cache: Dict[str, str] = {"": parent_id}

        for path in paths:
            parts = path.split("/")
            current_parent_id = parent_id
            for i, part in enumerate(parts):
                partial_path = "/".join(parts[:i + 1])
                if partial_path not in folder_cache:
                    folder_meta = self._create_folder(current_parent_id, part)
                    folder_cache[partial_path] = folder_meta["id"]
                current_parent_id = folder_cache[partial_path]

    def upload_document(
        self,
        folder_item_id: str,
        file_path: Path,
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a document to a SharePoint folder.

        Args:
            folder_item_id: Target folder's SharePoint item ID.
            file_path: Local path to the file to upload.
            file_name: Override the filename in SharePoint. Defaults to file_path.name.

        Returns:
            Dict: Uploaded file metadata (id, webUrl, etc.).
        """
        site_id = self._get_site_id()
        drive_id = self._get_drive_id()
        name = file_name or file_path.name

        with open(file_path, "rb") as f:
            content = f.read()

        # Reason: Use upload session for files > 4MB per Graph API best practice
        if len(content) > 4 * 1024 * 1024:
            return self._upload_large_file(folder_item_id, name, content)

        resp = self._graph_request(
            "PUT",
            f"{GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/items/{folder_item_id}:/{name}:/content",
            data=content,
            timeout=120,
        )
        return resp.json()

    def _upload_large_file(
        self, folder_item_id: str, file_name: str, content: bytes
    ) -> Dict[str, Any]:
        """Upload files > 4MB using Graph API upload session."""
        site_id = self._get_site_id()
        drive_id = self._get_drive_id()

        # Create upload session
        session_resp = self._graph_request(
            "POST",
            f"{GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/items/{folder_item_id}:/{file_name}:/createUploadSession",
            json={"item": {"@microsoft.graph.conflictBehavior": "rename"}},
            timeout=30,
        )
        upload_url = session_resp.json()["uploadUrl"]

        # Upload in 5MB chunks
        chunk_size = 5 * 1024 * 1024
        total_size = len(content)
        for start in range(0, total_size, chunk_size):
            chunk = content[start:start + chunk_size]
            end = min(start + chunk_size - 1, total_size - 1)
            requests.put(
                upload_url,
                data=chunk,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{total_size}",
                    "Content-Length": str(len(chunk)),
                },
                timeout=120,
            )

        # Final response from last chunk
        return {"webUrl": "", "name": file_name, "status": "uploaded"}

    def create_sharing_link(
        self,
        item_id: str,
        link_type: str = "view",
        scope: str = "organization",
    ) -> str:
        """
        Create a sharing link for a file or folder.

        Args:
            item_id: SharePoint item ID.
            link_type: "view" or "edit".
            scope: "organization" (internal) or "anonymous" (external, if allowed).

        Returns:
            str: Sharing link URL.
        """
        site_id = self._get_site_id()
        drive_id = self._get_drive_id()
        resp = self._graph_request(
            "POST",
            f"{GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/items/{item_id}/createLink",
            json={"type": link_type, "scope": scope},
            timeout=30,
        )
        return resp.json().get("link", {}).get("webUrl", "")
