"""Reusable, strict base model for SSZ types."""

from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    """
    Immutable, strict base model for all SSZ types.

    - Frozen: attribute assignment after construction raises
    - Extra forbidden: unknown fields rejected at construction
    - Strict: no implicit type coercion
    """

    model_config = ConfigDict(
        validate_default=True,
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
        strict=True,
    )
