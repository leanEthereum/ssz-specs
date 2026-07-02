"""Language-neutral reasons the spec rejects an invalid input."""

from enum import StrEnum


class RejectionReason(StrEnum):
    """Language-neutral reason the spec rejects an invalid input."""

    DECODE_ERROR = "DECODE_ERROR"
    """The wire bytes could not be decoded into a valid value of the target type."""
