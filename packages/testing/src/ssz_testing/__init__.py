"""Test tools for generating SSZ conformance test vectors."""

from collections.abc import Callable

from ssz_testing.fixtures import (
    FIXTURE_FORMATS,
    ExpectedRejection,
    SSZFixture,
    SSZTest,
)
from ssz_testing.rejection import RejectionReason

SSZTestFiller = Callable[..., SSZFixture]
"""Type of the ssz_test fixture: builds, generates, and collects an SSZ vector."""

__all__ = [
    "FIXTURE_FORMATS",
    "ExpectedRejection",
    "RejectionReason",
    "SSZFixture",
    "SSZTest",
    "SSZTestFiller",
]
