"""
Unanet CRM Integration Client.

Handles bidirectional sync between the local proposals database and
Unanet CRM via REST API. Field mapping is driven by unanet_mapping.json
so it can be adjusted without code changes.

Configuration (all via environment variables):
    UNANET_BASE_URL  — e.g., https://yourcompany.unanet.biz/
    UNANET_API_KEY   — API key from Unanet admin settings
    UNANET_COMPANY   — Company short name (part of URL)
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)

# Default field mapping file — override by setting UNANET_MAPPING_FILE env var
DEFAULT_MAPPING_FILE = Path(__file__).parent / "unanet_mapping.json"


class UnanetAuthError(Exception):
    """Raised when Unanet authentication fails."""
    pass


class UnanetAPIError(Exception):
    """Raised on non-2xx Unanet API responses."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Unanet API error {status_code}: {message}")


class UnanetClient:
    """
    Unanet CRM REST API client.

    Supports opportunity create/read/update and activity logging.
    Uses retry logic with exponential backoff for transient errors.

    Example:
        client = UnanetClient()
        crm_id = client.create_opportunity(proposal)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        mapping_file: Optional[Path] = None,
    ):
        """
        Initialize Unanet client from environment variables.

        Args:
            base_url: Override UNANET_BASE_URL env var.
            api_key: Override UNANET_API_KEY env var.
            mapping_file: Override path to field mapping JSON.

        Raises:
            ValueError: If base_url or api_key not provided or in environment.
        """
        self.base_url = (base_url or os.getenv("UNANET_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("UNANET_API_KEY", "")

        if not self.base_url:
            raise ValueError("UNANET_BASE_URL must be set in environment or passed directly")
        if not self.api_key:
            raise ValueError("UNANET_API_KEY must be set in environment or passed directly")

        # Load field mapping config
        mapping_path = mapping_file or Path(
            os.getenv("UNANET_MAPPING_FILE", str(DEFAULT_MAPPING_FILE))
        )
        if mapping_path.exists():
            with open(mapping_path) as f:
                _mapping_doc = json.load(f)
            # Reason: mapping JSON now has nested keys to support multiple mapping tables
            self.field_mapping: Dict[str, str] = _mapping_doc.get(
                "field_mapping", _mapping_doc  # backwards-compat with flat format
            )
            self._stage_map: Dict[str, str] = _mapping_doc.get("stage_mapping", {})
            self._reverse_stage_map: Dict[str, str] = _mapping_doc.get("reverse_stage_mapping", {})
        else:
            logger.warning("Unanet mapping file not found at %s — using defaults", mapping_path)
            self.field_mapping = self._default_mapping()
            self._stage_map = {}
            self._reverse_stage_map = {}

        # HTTP session with retry logic
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        """Build a requests.Session with auth headers and retry logic."""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        # Retry on connection errors and 5xx responses
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.mount("http://", HTTPAdapter(max_retries=retry))
        return session

    def _default_mapping(self) -> Dict[str, str]:
        """
        Default field mapping: local proposal field → Unanet field name.

        Returns:
            Dict[str, str]: Mapping dictionary.
        """
        return {
            "solicitation_number": "external_id",
            "title": "name",
            "pipeline_stage": "stage_code",
            "estimated_value": "potential_revenue",
            "proposal_due_date": "close_date",
            "capture_manager": "owner_username",
            "agency": "client_name",
            "bid_decision": "bid_decision",
            "pwin_score": "probability",
            "naics_code": "naics",
            "set_aside_type": "set_aside",
            "notes": "description",
        }

    def _map_proposal_to_crm(self, proposal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map local proposal fields to Unanet field names.

        Args:
            proposal_data: Proposal data dict (from Proposal.model_dump()).

        Returns:
            Dict[str, Any]: Unanet-formatted opportunity payload.
        """
        crm_data: Dict[str, Any] = {}
        for local_field, crm_field in self.field_mapping.items():
            value = proposal_data.get(local_field)
            if value is not None:
                # Reason: pwin stored as 0.0-1.0 locally; Unanet expects 0-100
                if local_field == "pwin_score" and value is not None:
                    value = float(value) * 100
                # Reason: Unanet stage codes differ from local stage names
                if local_field == "pipeline_stage":
                    value = self._map_stage(str(value))
                crm_data[crm_field] = value
        return crm_data

    def _map_stage(self, local_stage: str) -> str:
        """
        Map local pipeline stage to Unanet stage code.

        Stage mapping is driven by unanet_mapping.json (stage_mapping key).
        Actual stage codes used:
            01-Qualification, 02-Long Lead, 03-Bid Decision, 04-In Progress,
            05-Waiting/Review, 06-In Negotiation, 07-Closed Won, 08-Closed Lost,
            09-Closed No Bid, 20-Closed Other Reason,
            98-Awarded-Contract Vehicle, 99-Completed Contract Vehicle

        Args:
            local_stage: Local PipelineStage value string.

        Returns:
            str: Unanet stage code string.
        """
        # Primary: use stage_mapping from JSON (loaded in __init__)
        if self._stage_map:
            mapped = self._stage_map.get(local_stage)
            if mapped and not mapped.startswith("_"):
                return mapped
        # Fallback: use hardcoded canonical mapping
        _fallback = {
            "identified":                "01-Qualification",
            "qualifying":                "01-Qualification",
            "long_lead":                 "02-Long Lead",
            "bid_decision":              "03-Bid Decision",
            "active":                    "04-In Progress",
            "submitted":                 "05-Waiting/Review",
            "negotiating":               "06-In Negotiation",
            "awarded":                   "07-Closed Won",
            "lost":                      "08-Closed Lost",
            "no_bid":                    "09-Closed No Bid",
            "cancelled":                 "20-Closed Other Reason",
            "contract_vehicle_won":      "98-Awarded-Contract Vehicle",
            "contract_vehicle_complete": "99-Completed Contract Vehicle",
        }
        return _fallback.get(local_stage, local_stage)

    def map_stage_from_crm(self, unanet_stage: str) -> str:
        """
        Map a Unanet stage code back to a local PipelineStage value.

        Used when pulling opportunity updates from Unanet CRM.

        Args:
            unanet_stage: Unanet stage code string (e.g., "04-In Progress").

        Returns:
            str: Local PipelineStage value (e.g., "active").
        """
        if self._reverse_stage_map:
            mapped = self._reverse_stage_map.get(unanet_stage)
            if mapped and not mapped.startswith("_"):
                return mapped
        _fallback = {
            "01-Qualification":               "qualifying",
            "02-Long Lead":                   "long_lead",
            "03-Bid Decision":                "bid_decision",
            "04-In Progress":                 "active",
            "05-Waiting/Review":              "submitted",
            "06-In Negotiation":              "negotiating",
            "07-Closed Won":                  "awarded",
            "08-Closed Lost":                 "lost",
            "09-Closed No Bid":               "no_bid",
            "20-Closed Other Reason":         "cancelled",
            "98-Awarded-Contract Vehicle":    "contract_vehicle_won",
            "99-Completed Contract Vehicle":  "contract_vehicle_complete",
        }
        return _fallback.get(unanet_stage, "qualifying")

    def _raise_for_status(self, response: requests.Response) -> None:
        """Raise UnanetAPIError for non-2xx responses."""
        if not response.ok:
            try:
                detail = response.json().get("message", response.text)
            except Exception:
                detail = response.text
            raise UnanetAPIError(response.status_code, detail)

    def test_connection(self) -> bool:
        """
        Test API connectivity and authentication.

        Returns:
            bool: True if connection is successful.

        Raises:
            UnanetAuthError: If authentication fails.
        """
        try:
            resp = self._session.get(f"{self.base_url}/rest/opportunity", timeout=10)
            if resp.status_code == 401:
                raise UnanetAuthError("Invalid UNANET_API_KEY")
            self._raise_for_status(resp)
            return True
        except requests.ConnectionError as e:
            logger.error("Cannot connect to Unanet at %s: %s", self.base_url, e)
            return False

    def create_opportunity(self, proposal_data: Dict[str, Any]) -> str:
        """
        Create a new opportunity in Unanet CRM.

        Args:
            proposal_data: Proposal.model_dump() dict.

        Returns:
            str: Unanet CRM opportunity ID.

        Raises:
            UnanetAPIError: On API failure.
        """
        payload = self._map_proposal_to_crm(proposal_data)
        resp = self._session.post(
            f"{self.base_url}/rest/opportunity",
            json=payload,
            timeout=30,
        )
        self._raise_for_status(resp)
        crm_id = resp.json().get("id") or resp.json().get("opportunityId", "")
        logger.info("Created Unanet opportunity %s for %s", crm_id, proposal_data.get("solicitation_number"))
        return str(crm_id)

    def update_opportunity(self, crm_id: str, proposal_data: Dict[str, Any]) -> bool:
        """
        Update an existing Unanet opportunity.

        Args:
            crm_id: Unanet CRM opportunity ID.
            proposal_data: Fields to update (will be mapped).

        Returns:
            bool: True on success.
        """
        payload = self._map_proposal_to_crm(proposal_data)
        resp = self._session.put(
            f"{self.base_url}/rest/opportunity/{crm_id}",
            json=payload,
            timeout=30,
        )
        self._raise_for_status(resp)
        logger.info("Updated Unanet opportunity %s", crm_id)
        return True

    def get_opportunity(self, crm_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an opportunity from Unanet by CRM ID.

        Args:
            crm_id: Unanet CRM opportunity ID.

        Returns:
            Dict or None if not found.
        """
        resp = self._session.get(
            f"{self.base_url}/rest/opportunity/{crm_id}",
            timeout=30,
        )
        if resp.status_code == 404:
            return None
        self._raise_for_status(resp)
        return resp.json()

    def list_opportunities(
        self,
        stage_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List opportunities from Unanet CRM.

        Args:
            stage_filter: Optional Unanet stage code filter.
            limit: Maximum number of records to return.

        Returns:
            List[Dict]: Opportunity records.
        """
        params: Dict[str, Any] = {"limit": limit}
        if stage_filter:
            params["stage"] = stage_filter
        resp = self._session.get(
            f"{self.base_url}/rest/opportunity",
            params=params,
            timeout=30,
        )
        self._raise_for_status(resp)
        data = resp.json()
        return data if isinstance(data, list) else data.get("items", [])

    def log_activity(
        self,
        crm_id: str,
        activity_type: str,
        description: str,
        date: Optional[str] = None,
    ) -> bool:
        """
        Log an activity against a Unanet opportunity.

        Args:
            crm_id: Unanet CRM opportunity ID.
            activity_type: Activity type (e.g., "NOTE", "CALL", "MEETING").
            description: Activity description text.
            date: ISO date string (defaults to today).

        Returns:
            bool: True on success.
        """
        from datetime import date as date_type
        payload = {
            "type": activity_type,
            "description": description,
            "date": date or date_type.today().isoformat(),
        }
        resp = self._session.post(
            f"{self.base_url}/rest/opportunity/{crm_id}/activity",
            json=payload,
            timeout=30,
        )
        self._raise_for_status(resp)
        return True
