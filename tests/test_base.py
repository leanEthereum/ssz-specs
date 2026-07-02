"""Tests for the reusable strict base model."""

import pytest
from pydantic import ValidationError

from ssz.base import StrictBaseModel


class StrictExample(StrictBaseModel):
    """A strict model used to exercise the frozen, extra-forbid, and strict constraints."""

    first_value: int


def test_strict_model_rejects_attribute_assignment() -> None:
    """A frozen strict model raises when an attribute is reassigned after construction."""
    instance = StrictExample(first_value=1)
    with pytest.raises(ValidationError):
        instance.first_value = 2


def test_strict_model_rejects_unknown_fields() -> None:
    """A strict model forbids extra fields at construction."""
    with pytest.raises(ValidationError):
        StrictExample(first_value=1, unexpected=2)  # type: ignore[call-arg]


def test_strict_model_rejects_implicit_type_coercion() -> None:
    """Strict mode rejects a value that would otherwise coerce into the declared type."""
    with pytest.raises(ValidationError):
        StrictExample(first_value="1")  # type: ignore[arg-type]
