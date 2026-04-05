"""
server/request_models.py — Pydantic request/response models.

Used for validating and coercing incoming JSON bodies before they reach
business logic.  Import the model you need and call `.model_validate(data)`
on the parsed dict from `handler.get_request_body()`.

If Pydantic is unavailable the module degrades gracefully to plain dicts,
so the server still starts even if pydantic is not installed.
"""

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field, field_validator
    _PYDANTIC = True
except ImportError:
    _PYDANTIC = False


# ---------------------------------------------------------------------------
# Opportunity models
# ---------------------------------------------------------------------------

if _PYDANTIC:
    class OpportunityCreateRequest(BaseModel):
        """Request body for POST /api/opportunities."""

        name: str = Field(..., min_length=1, max_length=500,
                          description="Opportunity name (required)")
        description: str = Field("", max_length=5000)
        status: str = Field("open",
                            pattern=r'^(open|in_progress|won|lost)$')
        pipeline_stage: str = Field("identified")
        priority: str = Field("medium",
                              pattern=r'^(low|medium|high)$')
        value: float = Field(0.0, ge=0)
        tags: List[str] = Field(default_factory=list)
        metadata: Dict[str, Any] = Field(default_factory=dict)

        @field_validator('name')
        @classmethod
        def name_not_blank(cls, v: str) -> str:
            """Reject whitespace-only names."""
            if not v.strip():
                raise ValueError("name must not be blank")
            return v.strip()

        @field_validator('tags')
        @classmethod
        def clean_tags(cls, v: List[str]) -> List[str]:
            """Strip whitespace from each tag and drop empties."""
            return [t.strip() for t in v if t.strip()]

    class OpportunityUpdateRequest(BaseModel):
        """Request body for PUT/PATCH /api/opportunities/{id}."""

        name: Optional[str] = Field(None, min_length=1, max_length=500)
        description: Optional[str] = Field(None, max_length=5000)
        status: Optional[str] = Field(None,
                                      pattern=r'^(open|in_progress|won|lost)$')
        pipeline_stage: Optional[str] = None
        priority: Optional[str] = Field(None,
                                        pattern=r'^(low|medium|high)$')
        value: Optional[float] = Field(None, ge=0)
        tags: Optional[List[str]] = None
        metadata: Optional[Dict[str, Any]] = None

    class CsvImportParseRequest(BaseModel):
        """Request body for POST /api/opportunities/import/parse."""

        csv_content: str = Field(..., min_length=1)

    class CsvImportConfirmRequest(BaseModel):
        """Request body for POST /api/opportunities/import/confirm."""

        csv_content: str = Field(..., min_length=1)
        field_map: Dict[str, str] = Field(...,
                                          description="csv_column → opportunity_field mapping")

else:
    # Fallback stubs — just pass dicts through unchanged
    class _Stub:
        """No-op stub used when Pydantic is not installed."""

        @classmethod
        def model_validate(cls, data: Dict) -> Dict:
            return data

        @classmethod
        def model_dump(cls) -> Dict:
            return {}

    OpportunityCreateRequest = _Stub
    OpportunityUpdateRequest = _Stub
    CsvImportParseRequest = _Stub
    CsvImportConfirmRequest = _Stub


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------

def validate_or_error(model_cls, data: Any):
    """
    Validate `data` against `model_cls` and return (model_instance, None)
    on success or (None, error_message) on failure.

    Args:
        model_cls: A Pydantic model class.
        data: Parsed JSON dict from request body.

    Returns:
        tuple: (validated_model | None, error_str | None)
    """
    if not _PYDANTIC:
        return data, None
    try:
        return model_cls.model_validate(data), None
    except Exception as exc:
        # Pydantic v2 ValidationError has `.errors()` for detail
        errors = getattr(exc, 'errors', None)
        if callable(errors):
            detail = "; ".join(
                f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}"
                for e in errors()
            )
        else:
            detail = str(exc)
        return None, detail
