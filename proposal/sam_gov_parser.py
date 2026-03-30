"""
SAM.gov Parser — Feed ingestion for opportunity-curator skill.

Fetches opportunities from the SAM.gov Opportunities API v2 and converts
them into OpportunityInput objects for scoring.

Configuration via environment variables (see .env.example):
    SAM_GOV_API_KEY      — api.sam.gov API key (required for non-public data)
    SAM_GOV_BASE_URL     — override base URL (default: https://api.sam.gov)
    SAM_GOV_PAGE_SIZE    — records per page (default: 100, max: 1000)
    SAM_GOV_MAX_PAGES    — max pages to fetch per run (default: 5)
    COMPANY_NAICS_CODES  — comma-separated NAICS codes to filter results

API docs: https://open.gsa.gov/api/get-opportunities-public-api/
"""

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Iterator, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from proposal.opportunity_scorer import OpportunityInput

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / defaults
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "https://api.sam.gov"
_OPPORTUNITIES_PATH = "/opportunities/v2/search"
_DEFAULT_PAGE_SIZE = 100
_DEFAULT_MAX_PAGES = 5
_REQUEST_TIMEOUT = 30          # seconds per request
_RETRY_TOTAL = 3
_RETRY_BACKOFF = 1.0           # seconds

# SAM.gov set-aside code → internal label mapping
_SET_ASIDE_MAP: Dict[str, str] = {
    "SBA":   "small_business",
    "SBP":   "small_business",   # Total Small Business Set-Aside (FAR 19.5)
    "8A":    "8a",
    "8AN":   "8a",
    "HZC":   "hubzone",
    "HZS":   "hubzone",
    "SDVOSBC": "sdvosb",
    "SDVOSBS": "sdvosb",
    "WOSB":  "wosb",
    "WOSBSS": "wosb",
    "EDWOSB": "wosb",
    "EDWOSBSS": "wosb",
    "VSB":   "vosb",
    "":      "full_and_open",
}

# Notice types to include (exclude Awards, Justifications, etc.)
_SOLICITATION_TYPES = {
    "o",    # Solicitation
    "k",    # Combined Synopsis/Solicitation
    "p",    # Presolicitation
    "r",    # Sources Sought
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FetchConfig:
    """
    Configuration for a SAM.gov fetch run.

    Attributes:
        naics_codes: Filter by these NAICS codes (OR logic). Empty = no filter.
        posted_from: Only opportunities posted on/after this date.
        posted_to: Only opportunities posted on/before this date.
        notice_types: SAM.gov notice type codes to include.
        keywords: Free-text keyword search (combined with AND).
        page_size: Records per page.
        max_pages: Stop after this many pages (safety cap).
        include_expired: If True, include opportunities past responseDeadLine.
    """
    naics_codes: List[str] = field(default_factory=list)
    posted_from: Optional[datetime] = None
    posted_to: Optional[datetime] = None
    notice_types: List[str] = field(default_factory=lambda: list(_SOLICITATION_TYPES))
    keywords: str = ""
    page_size: int = _DEFAULT_PAGE_SIZE
    max_pages: int = _DEFAULT_MAX_PAGES
    include_expired: bool = False

    @classmethod
    def from_env(cls, **overrides) -> "FetchConfig":
        """
        Build a FetchConfig from environment variables with optional overrides.

        Returns:
            FetchConfig populated from environment.
        """
        raw_naics = os.getenv("COMPANY_NAICS_CODES", "")
        naics = [n.strip() for n in raw_naics.split(",") if n.strip()] if raw_naics else []
        return cls(
            naics_codes=overrides.get("naics_codes", naics),
            page_size=int(os.getenv("SAM_GOV_PAGE_SIZE", str(_DEFAULT_PAGE_SIZE))),
            max_pages=int(os.getenv("SAM_GOV_MAX_PAGES", str(_DEFAULT_MAX_PAGES))),
            posted_from=overrides.get("posted_from", datetime.now() - timedelta(days=30)),
            **{k: v for k, v in overrides.items() if k not in ("naics_codes", "posted_from")},
        )


@dataclass
class FetchResult:
    """
    Summary of a SAM.gov fetch run.

    Attributes:
        opportunities: Parsed OpportunityInput objects ready for scoring.
        total_returned: Total records returned by SAM.gov (may exceed fetched).
        pages_fetched: Number of pages fetched in this run.
        errors: Non-fatal errors encountered (e.g., parse failures).
        fetched_at: ISO timestamp when this run completed.
    """
    opportunities: List[OpportunityInput]
    total_returned: int
    pages_fetched: int
    errors: List[str] = field(default_factory=list)
    fetched_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# HTTP session factory
# ---------------------------------------------------------------------------

def _build_session(api_key: str) -> requests.Session:
    """
    Build a requests.Session with retry logic and auth header.

    Args:
        api_key: SAM.gov API key (empty string for public-only access).

    Returns:
        requests.Session: Configured session.
    """
    session = requests.Session()

    retry = Retry(
        total=_RETRY_TOTAL,
        backoff_factor=_RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    if api_key:
        session.headers["X-Api-Key"] = api_key

    return session


# ---------------------------------------------------------------------------
# SAM.gov API interaction
# ---------------------------------------------------------------------------

def _build_params(config: FetchConfig, offset: int) -> Dict[str, Any]:
    """
    Build query parameters for one SAM.gov API request.

    Args:
        config: Fetch configuration.
        offset: Record offset for pagination.

    Returns:
        Dict[str, Any]: Query parameters dict.
    """
    params: Dict[str, Any] = {
        "limit": config.page_size,
        "offset": offset,
    }

    if config.naics_codes:
        params["naicsCodes"] = ",".join(config.naics_codes)

    if config.posted_from:
        params["postedFrom"] = config.posted_from.strftime("%m/%d/%Y")

    if config.posted_to:
        params["postedTo"] = config.posted_to.strftime("%m/%d/%Y")

    if config.notice_types:
        params["ptype"] = ",".join(config.notice_types)

    if config.keywords:
        params["q"] = config.keywords

    if not config.include_expired:
        params["active"] = "true"

    return params


def _fetch_page(
    session: requests.Session,
    base_url: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Fetch one page from the SAM.gov Opportunities API.

    Args:
        session: Configured requests session.
        base_url: Base URL for SAM.gov.
        params: Query parameters.

    Returns:
        Dict[str, Any]: Parsed JSON response body.

    Raises:
        requests.HTTPError: On non-2xx response after retries.
        requests.RequestException: On network error after retries.
    """
    url = f"{base_url}{_OPPORTUNITIES_PATH}"
    resp = session.get(url, params=params, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Record parsing
# ---------------------------------------------------------------------------

def _parse_set_aside(record: Dict[str, Any]) -> str:
    """
    Extract and normalize set-aside type from a SAM.gov record.

    Args:
        record: SAM.gov opportunity JSON record.

    Returns:
        str: Internal set-aside label (e.g., 'small_business', '8a').
    """
    type_of_set_aside = (record.get("typeOfSetAsideDescription") or "").upper()
    set_aside_code = (record.get("typeOfSetAside") or "").upper()

    # Try code lookup first, then description-based fallback
    if set_aside_code in _SET_ASIDE_MAP:
        return _SET_ASIDE_MAP[set_aside_code]

    lower_desc = type_of_set_aside.lower()
    if "sdvosb" in lower_desc:
        return "sdvosb"
    if "8(a)" in lower_desc or "8a" in lower_desc:
        return "8a"
    if "hubzone" in lower_desc:
        return "hubzone"
    if "wosb" in lower_desc:
        return "wosb"
    if "small business" in lower_desc:
        return "small_business"
    if "vosb" in lower_desc:
        return "vosb"

    return "full_and_open" if not type_of_set_aside else "other"


def _parse_due_date(record: Dict[str, Any]) -> Optional[str]:
    """
    Extract proposal due date from a SAM.gov record.

    SAM.gov stores this as responseDeadLine in ISO format or as a date string.

    Args:
        record: SAM.gov opportunity JSON record.

    Returns:
        Optional[str]: ISO date string 'YYYY-MM-DD' or None.
    """
    raw = record.get("responseDeadLine") or record.get("archiveDate")
    if not raw:
        return None
    # SAM.gov may return various formats
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw[:19].replace("Z", ""), fmt.replace("%z", "")).strftime("%Y-%m-%d")
        except ValueError:
            continue
    logger.debug("Could not parse date: %s", raw)
    return None


def _parse_value(record: Dict[str, Any]) -> float:
    """
    Extract estimated contract value from a SAM.gov record.

    Args:
        record: SAM.gov opportunity JSON record.

    Returns:
        float: Estimated value in dollars (0.0 if unavailable).
    """
    award = record.get("award") or {}
    value_str = str(award.get("amount") or record.get("estimatedValue") or "0")
    try:
        return float(value_str.replace(",", "").replace("$", "").strip() or "0")
    except (ValueError, AttributeError):
        return 0.0


def _record_to_input(record: Dict[str, Any]) -> Optional[OpportunityInput]:
    """
    Convert a single SAM.gov JSON record to an OpportunityInput.

    Args:
        record: SAM.gov opportunity JSON record.

    Returns:
        Optional[OpportunityInput]: Parsed input, or None if record is unusable.
    """
    title = (record.get("title") or "").strip()
    if not title:
        return None

    office = record.get("officeAddress") or {}
    agency = (
        record.get("departmentName")
        or record.get("subtierName")
        or office.get("city")
        or ""
    )

    naics_code = (record.get("naicsCode") or "").strip()
    sol_number = (record.get("solicitationNumber") or record.get("noticeId") or "").strip()

    # Description: combine synopsis fields
    description_parts = [
        record.get("description") or "",
        record.get("additionalInfoLink") or "",
    ]
    description = " ".join(p for p in description_parts if p).strip()

    return OpportunityInput(
        title=title,
        agency=agency,
        naics_code=naics_code,
        set_aside_type=_parse_set_aside(record),
        estimated_value=_parse_value(record),
        source="SAM.gov",
        description=description,
        solicitation_number=sol_number,
        proposal_due_date=_parse_due_date(record),
        is_recompete="recompete" in title.lower() or "re-compete" in title.lower(),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_opportunities(config: Optional[FetchConfig] = None) -> FetchResult:
    """
    Fetch and parse opportunities from SAM.gov.

    Paginates automatically up to config.max_pages. Non-fatal parse errors
    are collected in FetchResult.errors rather than raising.

    Args:
        config: Fetch configuration. Defaults to FetchConfig.from_env().

    Returns:
        FetchResult: Parsed opportunities and run metadata.
    """
    if config is None:
        config = FetchConfig.from_env()

    api_key = os.getenv("SAM_GOV_API_KEY", "")
    base_url = os.getenv("SAM_GOV_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")

    if not api_key:
        logger.warning("SAM_GOV_API_KEY not set — public data only (rate-limited)")

    session = _build_session(api_key)
    opportunities: List[OpportunityInput] = []
    errors: List[str] = []
    total_returned = 0
    offset = 0

    pages_fetched = 0
    for page_num in range(config.max_pages):
        pages_fetched = page_num + 1
        params = _build_params(config, offset)
        try:
            data = _fetch_page(session, base_url, params)
        except requests.HTTPError as exc:
            errors.append(f"HTTP error on page {pages_fetched}: {exc}")
            break
        except requests.RequestException as exc:
            errors.append(f"Network error on page {pages_fetched}: {exc}")
            break

        records = data.get("opportunitiesData") or []
        total_returned = int(data.get("totalRecords") or len(records))

        for record in records:
            try:
                opp = _record_to_input(record)
                if opp:
                    opportunities.append(opp)
            except Exception as exc:  # noqa: BLE001
                notice_id = record.get("noticeId", "unknown")
                errors.append(f"Parse error for noticeId={notice_id}: {exc}")

        logger.info(
            "SAM.gov page %d/%d: %d records (total reported: %d)",
            pages_fetched, config.max_pages, len(records), total_returned,
        )

        if len(records) < config.page_size:
            # Last page
            break

        offset += config.page_size
        # Respect SAM.gov rate limits between pages
        time.sleep(0.25)

    return FetchResult(
        opportunities=opportunities,
        total_returned=total_returned,
        pages_fetched=pages_fetched,
        errors=errors,
    )


def iter_opportunities(config: Optional[FetchConfig] = None) -> Iterator[OpportunityInput]:
    """
    Yield OpportunityInput objects one at a time from a SAM.gov fetch.

    Convenience wrapper around fetch_opportunities for streaming use cases.

    Args:
        config: Fetch configuration. Defaults to FetchConfig.from_env().

    Yields:
        OpportunityInput: One opportunity at a time.
    """
    result = fetch_opportunities(config)
    if result.errors:
        logger.warning("Fetch completed with %d errors: %s", len(result.errors), result.errors[:3])
    yield from result.opportunities


def fetch_by_solicitation(solicitation_number: str) -> Optional[OpportunityInput]:
    """
    Fetch a single opportunity by its solicitation number.

    Args:
        solicitation_number: SAM.gov solicitation number (e.g., 'FA8612-25-R-0001').

    Returns:
        Optional[OpportunityInput]: The opportunity, or None if not found.
    """
    api_key = os.getenv("SAM_GOV_API_KEY", "")
    base_url = os.getenv("SAM_GOV_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
    session = _build_session(api_key)

    params = {
        "solnum": solicitation_number,
        "limit": 1,
        "offset": 0,
    }

    try:
        data = _fetch_page(session, base_url, params)
    except requests.RequestException as exc:
        logger.error("Failed to fetch solicitation %s: %s", solicitation_number, exc)
        return None

    records = data.get("opportunitiesData") or []
    if not records:
        logger.info("Solicitation %s not found in SAM.gov", solicitation_number)
        return None

    return _record_to_input(records[0])
