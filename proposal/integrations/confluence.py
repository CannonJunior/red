"""
Confluence Integration Client — Atlassian REST API v2.

Creates and manages Confluence spaces and pages for proposal knowledge management.
Each proposal gets its own Confluence space with a standard page hierarchy.

Configuration (all via environment variables):
    CONFLUENCE_BASE_URL   — e.g., https://yourcompany.atlassian.net
    CONFLUENCE_EMAIL      — Atlassian account email
    CONFLUENCE_API_TOKEN  — API token from https://id.atlassian.com/manage-profile/security/api-tokens
    CONFLUENCE_SPACE_PREFIX — Prefix for space keys (default: PROP)

Note: For on-premise Confluence, use username + password or personal token.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

# Jinja2 template directory for Confluence page bodies
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "proposal" / "confluence"


class ConfluenceAPIError(Exception):
    """Raised on non-2xx Confluence API responses."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Confluence API error {status_code}: {message}")


class ConfluenceClient:
    """
    Atlassian Confluence REST API client.

    Creates proposal knowledge spaces with standard page structure.
    Supports page creation from Jinja2 templates for consistent formatting.

    Example:
        client = ConfluenceClient()
        space_key = client.create_proposal_space("FA8612-26-R-0001", "My Effort")
        client.create_meeting_notes_page(space_key, "kickoff", "2026-03-30", "...")
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        space_prefix: Optional[str] = None,
    ):
        """
        Initialize Confluence client from environment variables.

        Args:
            base_url: Override CONFLUENCE_BASE_URL.
            email: Override CONFLUENCE_EMAIL.
            api_token: Override CONFLUENCE_API_TOKEN.
            space_prefix: Override CONFLUENCE_SPACE_PREFIX.

        Raises:
            ValueError: If required configuration is missing.
        """
        self.base_url = (base_url or os.getenv("CONFLUENCE_BASE_URL", "")).rstrip("/")
        self.email = email or os.getenv("CONFLUENCE_EMAIL", "")
        self.api_token = api_token or os.getenv("CONFLUENCE_API_TOKEN", "")
        self.space_prefix = space_prefix or os.getenv("CONFLUENCE_SPACE_PREFIX", "PROP")

        if not self.base_url:
            raise ValueError("CONFLUENCE_BASE_URL must be set in environment")
        if not self.email or not self.api_token:
            raise ValueError(
                "CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN must be set. "
                "Generate a token at: https://id.atlassian.com/manage-profile/security/api-tokens"
            )

        self._auth = HTTPBasicAuth(self.email, self.api_token)
        self._api_v1 = f"{self.base_url}/wiki/rest/api"
        self._api_v2 = f"{self.base_url}/wiki/api/v2"

    def _request(
        self, method: str, url: str, **kwargs: Any
    ) -> requests.Response:
        """
        Execute a Confluence API request.

        Args:
            method: HTTP method.
            url: Full API URL.
            **kwargs: Additional requests arguments.

        Returns:
            requests.Response

        Raises:
            ConfluenceAPIError: On non-2xx response.
        """
        resp = requests.request(
            method, url, auth=self._auth,
            headers={"Content-Type": "application/json"},
            timeout=30,
            **kwargs,
        )
        if not resp.ok:
            try:
                detail = resp.json().get("message", resp.text)
            except Exception:
                detail = resp.text
            raise ConfluenceAPIError(resp.status_code, detail)
        return resp

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template to a Confluence storage format HTML string.

        Falls back to a simple text body if Jinja2 or template not available.

        Args:
            template_name: Template filename in templates/proposal/confluence/.
            context: Variables to inject into the template.

        Returns:
            str: Rendered HTML string in Confluence storage format.
        """
        try:
            from jinja2 import Environment, FileSystemLoader
            env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
            template = env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.warning("Could not render template %s: %s — using plain text", template_name, e)
            return f"<p>{context.get('body', 'Content pending.')}</p>"

    # ------------------------------------------------------------------
    # Space management
    # ------------------------------------------------------------------

    def _space_key(self, solicitation_number: str) -> str:
        """
        Generate a Confluence space key from solicitation number.

        Keys are alphanumeric, max 255 chars, uppercase.
        Example: FA8612-26-R-0001 → PROPFA8612

        Args:
            solicitation_number: Solicitation number string.

        Returns:
            str: Confluence space key.
        """
        import re
        clean = re.sub(r"[^A-Z0-9]", "", solicitation_number.upper())[:12]
        return f"{self.space_prefix}{clean}"

    def create_proposal_space(
        self,
        solicitation_number: str,
        title: str,
        description: str = "",
    ) -> str:
        """
        Create a Confluence space for a proposal.

        If the space already exists, returns the existing space key.

        Args:
            solicitation_number: Solicitation number (used to derive space key).
            title: Full proposal title.
            description: Optional space description.

        Returns:
            str: Confluence space key.
        """
        space_key = self._space_key(solicitation_number)
        space_title = f"{solicitation_number} — {title[:60]}"

        # Check if space already exists
        try:
            resp = self._request("GET", f"{self._api_v1}/space/{space_key}")
            logger.info("Confluence space %s already exists", space_key)
            return space_key
        except ConfluenceAPIError as e:
            if e.status_code != 404:
                raise

        # Create the space
        self._request("POST", f"{self._api_v1}/space", json={
            "key": space_key,
            "name": space_title,
            "description": {
                "plain": {
                    "value": description or f"Proposal workspace for {solicitation_number}",
                    "representation": "plain",
                }
            },
        })
        logger.info("Created Confluence space %s", space_key)

        # Create standard page structure
        self._create_standard_pages(space_key, solicitation_number, title)
        return space_key

    def _create_standard_pages(
        self, space_key: str, solicitation_number: str, title: str
    ) -> None:
        """Create the standard page hierarchy in a new proposal space."""
        pages = [
            {
                "title": "📋 Opportunity Brief",
                "template": "opportunity_brief.html",
                "context": {"solicitation_number": solicitation_number, "title": title},
            },
            {
                "title": "📊 Capture Plan & Win Strategy",
                "template": "capture_plan.html",
                "context": {"solicitation_number": solicitation_number},
            },
            {
                "title": "👥 Team & Organization",
                "template": "team_org.html",
                "context": {},
            },
            {
                "title": "📅 Proposal Schedule",
                "template": "proposal_schedule.html",
                "context": {},
            },
            {
                "title": "📝 Technical Notes",
                "template": "technical_notes.html",
                "context": {},
            },
            {
                "title": "🎨 Color Team Reviews",
                "template": "color_teams_index.html",
                "context": {},
            },
            {
                "title": "📞 Meeting Notes",
                "template": "meeting_notes_index.html",
                "context": {},
            },
            {
                "title": "🔁 Hotwash & Lessons Learned",
                "template": "hotwash.html",
                "context": {},
            },
        ]

        for page in pages:
            try:
                body = self._render_template(page["template"], page["context"])
                self.create_page(
                    space_key=space_key,
                    title=page["title"],
                    body=body,
                )
            except Exception as e:
                logger.warning("Could not create page '%s': %s", page["title"], e)

    # ------------------------------------------------------------------
    # Page management
    # ------------------------------------------------------------------

    def create_page(
        self,
        space_key: str,
        title: str,
        body: str,
        parent_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Confluence page with HTML body (storage format).

        Args:
            space_key: Target Confluence space key.
            title: Page title.
            body: Page body in Confluence storage format (HTML).
            parent_title: If set, makes this page a child of the named page.

        Returns:
            Dict: Created page metadata (id, _links.webui, etc.).
        """
        parent_id = None
        if parent_title:
            parent_id = self._find_page_id(space_key, parent_title)

        payload: Dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {"value": body, "representation": "storage"}
            },
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]

        resp = self._request("POST", f"{self._api_v1}/content", json=payload)
        page = resp.json()
        logger.info("Created Confluence page '%s' in space %s", title, space_key)
        return page

    def update_page(
        self, page_id: str, new_body: str, new_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing Confluence page.

        Args:
            page_id: Confluence page ID.
            new_body: New body content (storage format HTML).
            new_title: Optional new title.

        Returns:
            Dict: Updated page metadata.
        """
        # Get current version number
        current = self._request("GET", f"{self._api_v1}/content/{page_id}").json()
        current_version = current["version"]["number"]

        payload: Dict[str, Any] = {
            "type": "page",
            "title": new_title or current["title"],
            "version": {"number": current_version + 1},
            "body": {
                "storage": {"value": new_body, "representation": "storage"}
            },
        }
        resp = self._request("PUT", f"{self._api_v1}/content/{page_id}", json=payload)
        return resp.json()

    def _find_page_id(self, space_key: str, title: str) -> Optional[str]:
        """Find a page ID by title within a space."""
        resp = self._request(
            "GET",
            f"{self._api_v1}/content",
            params={"spaceKey": space_key, "title": title, "type": "page"},
        )
        results = resp.json().get("results", [])
        return results[0]["id"] if results else None

    # ------------------------------------------------------------------
    # Meeting notes
    # ------------------------------------------------------------------

    def create_meeting_notes_page(
        self,
        space_key: str,
        meeting_type: str,
        meeting_date: str,
        notes: str,
        attendees: Optional[List[str]] = None,
        action_items: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Create a meeting notes page as a child of the 'Meeting Notes' section.

        Args:
            space_key: Target Confluence space key.
            meeting_type: e.g., "Kickoff", "Pink Team", "Weekly Sync".
            meeting_date: ISO date string (e.g., 2026-03-30).
            notes: Meeting notes text (will be wrapped in Confluence markup).
            attendees: List of attendee names.
            action_items: List of dicts with keys: description, owner, due_date.

        Returns:
            Dict: Created page metadata with webUrl.
        """
        title = f"{meeting_type} — {meeting_date}"
        body = self._render_template("meeting_notes.html", {
            "meeting_type": meeting_type,
            "meeting_date": meeting_date,
            "notes": notes,
            "attendees": attendees or [],
            "action_items": action_items or [],
        })
        return self.create_page(
            space_key=space_key,
            title=title,
            body=body,
            parent_title="📞 Meeting Notes",
        )

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    def attach_file(self, page_id: str, file_path: Path) -> Dict[str, Any]:
        """
        Attach a local file to a Confluence page.

        Args:
            page_id: Confluence page ID.
            file_path: Local file path to attach.

        Returns:
            Dict: Attachment metadata.
        """
        with open(file_path, "rb") as f:
            resp = requests.post(
                f"{self._api_v1}/content/{page_id}/child/attachment",
                auth=self._auth,
                headers={"X-Atlassian-Token": "no-check"},
                files={"file": (file_path.name, f)},
                timeout=120,
            )
        if not resp.ok:
            raise ConfluenceAPIError(resp.status_code, resp.text)
        return resp.json()

    def get_page_url(self, page_id: str) -> str:
        """
        Get the web URL for a Confluence page.

        Args:
            page_id: Confluence page ID.

        Returns:
            str: Full web URL to the page.
        """
        resp = self._request(
            "GET",
            f"{self._api_v1}/content/{page_id}",
            params={"expand": "_links"},
        )
        links = resp.json().get("_links", {})
        base = links.get("base", self.base_url)
        web_ui = links.get("webui", "")
        return f"{base}{web_ui}"
