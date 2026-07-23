"""Tests for SSZModel and SSZType base class behavior."""

from typing import Any, cast

import pytest
from pydantic import ValidationError

from ssz import Uint8, Uint16, Uint64
from ssz.bitfields import BaseBitlist, BaseBitvector
from ssz.boolean import Boolean
from ssz.byte_arrays import BaseByteList
from ssz.collections import List, Vector
from ssz.container import Container
from ssz.exceptions import SSZTypeError, SSZValueError
from ssz.ssz_base import SSZCollection


class Uint16List4(List[Uint16]):
    """A list with up to 4 Uint16 values."""

    LIMIT = 4


class Uint16Vector2(Vector[Uint16]):
    """A vector of exactly 2 Uint16 values."""

    LENGTH = 2


class TwoFieldContainer(Container):
    """A container with two fixed-size fields."""

    x: Uint8
    y: Uint16


class ThreeFieldContainer(Container):
    """A container with three fields, one variable-size."""

    a: Uint8
    b: Uint64
    c: Uint16List4


class SmallBitlist(BaseBitlist):
    """A bitlist with a small limit, used to test SSZModel.__len__ data path."""

    LIMIT = 8


class SmallBitvector(BaseBitvector):
    """A bitvector with exactly 3 bits."""

    LENGTH = 3


class SmallByteList(BaseByteList):
    """A byte list with up to 10 bytes."""

    LIMIT = 10


class TestSSZModelLength:
    """
    Tests for SSZModel.__len__() on both collection and container models.

    Uses BaseBitlist (not List) for the data-path because List overrides
    __len__ with its own implementation. BaseBitlist inherits SSZModel's version.
    """

    def test_length_data_path_via_bitlist(self) -> None:
        """BaseBitlist delegates to SSZModel.__len__ which returns len(data)."""
        bl = SmallBitlist(data=(Boolean(True), Boolean(False), Boolean(True)))
        assert len(bl) == 3

    def test_length_empty_data_path_via_bitlist(self) -> None:
        bl = SmallBitlist(data=())
        assert len(bl) == 0

    def test_length_container_returns_field_count(self) -> None:
        container = TwoFieldContainer(x=Uint8(1), y=Uint16(2))
        assert len(container) == 2

    def test_length_three_field_container(self) -> None:
        container = ThreeFieldContainer(a=Uint8(5), b=Uint64(42), c=Uint16List4(data=[Uint16(1)]))
        assert len(container) == 3


class TestSSZModelRepr:
    """Tests for SSZModel.__repr__() on both collection and container models."""

    def test_repr_collection_shows_data(self) -> None:
        assert repr(Uint16List4(data=[Uint16(10), Uint16(20)])) == (
            "Uint16List4(data=[Uint16(10), Uint16(20)])"
        )

    def test_repr_empty_collection(self) -> None:
        assert repr(Uint16List4(data=[])) == "Uint16List4(data=[])"

    def test_repr_container_shows_fields(self) -> None:
        assert repr(TwoFieldContainer(x=Uint8(1), y=Uint16(2))) == (
            "TwoFieldContainer(x=Uint8(1) y=Uint16(2))"
        )

    def test_repr_three_field_container(self) -> None:
        container = ThreeFieldContainer(a=Uint8(5), b=Uint64(42), c=Uint16List4(data=[Uint16(1)]))
        assert repr(container) == (
            "ThreeFieldContainer(a=Uint8(5) b=Uint64(42) c=Uint16List4(data=[Uint16(1)]))"
        )


class TestSSZTypeEncodeDecode:
    """
    Tests for encode_bytes/decode_bytes on SSZType.

    These methods wrap the stream-based serialize/deserialize interface
    so callers can work with plain byte strings instead.
    """

    def test_encode_bytes_fixed_container(self) -> None:
        container = TwoFieldContainer(x=Uint8(1), y=Uint16(2))
        encoded = container.encode_bytes()
        assert encoded == b"\x01\x02\x00"

    def test_decode_bytes_fixed_container(self) -> None:
        assert TwoFieldContainer.decode_bytes(b"\x01\x02\x00") == TwoFieldContainer(
            x=Uint8(1), y=Uint16(2)
        )

    def test_encode_decode_roundtrip(self) -> None:
        """Encoding then decoding must recover the original object."""
        original = TwoFieldContainer(x=Uint8(255), y=Uint16(1000))
        assert TwoFieldContainer.decode_bytes(original.encode_bytes()) == original


class TestSSZCollectionMutation:
    """
    Tests for in-place collection mutation.

    Collections are mutable, unlike containers: element assignment, append,
    and pop validate the incoming elements and the resulting length by the
    same rules construction applies. Existing elements were validated when
    they entered, so mutation cost is proportional to the change rather than
    the collection size.
    """

    def test_setitem_replaces_and_coerces(self) -> None:
        """Integer index assignment coerces the value into the element type."""
        values = Uint16List4(data=[Uint16(1), Uint16(2)])
        values[1] = 9  # ty: ignore[invalid-assignment]
        assert values == Uint16List4(data=[Uint16(1), Uint16(9)])

    def test_setitem_slice_revalidates(self) -> None:
        """Slice assignment replaces a range of elements."""
        bits = SmallBitvector(data=[Boolean(True), Boolean(True), Boolean(True)])
        bits[1:] = [Boolean(False), Boolean(False)]
        assert bits == SmallBitvector(data=[Boolean(True), Boolean(False), Boolean(False)])

    def test_append_grows_within_limit(self) -> None:
        """Append adds one element while under the limit."""
        values = Uint16List4(data=[Uint16(1)])
        values.append(Uint16(2))
        assert values == Uint16List4(data=[Uint16(1), Uint16(2)])

    def test_append_beyond_limit_rejected(self) -> None:
        """Append past the limit fails revalidation and raises."""
        values = Uint16List4(data=[Uint16(1)] * 4)
        with pytest.raises((SSZValueError, ValidationError)):
            values.append(Uint16(5))

    def test_fixed_length_shapes_lack_append_and_pop(self) -> None:
        """Fixed-length shapes do not offer length-changing methods at all."""
        assert not hasattr(Uint16Vector2, "append")
        assert not hasattr(Uint16Vector2, "pop")
        assert not hasattr(SmallBitvector, "append")
        assert not hasattr(SmallBitvector, "pop")

    def test_setitem_slice_resize_on_fixed_length_rejected(self) -> None:
        """A slice assignment that would resize a fixed-length shape is rejected."""
        bits = SmallBitvector(data=[Boolean(True)] * 3)
        with pytest.raises(SSZValueError):
            bits[1:] = [Boolean(False)]
        assert bits == SmallBitvector(data=[Boolean(True)] * 3)

    def test_pop_returns_last_and_shrinks(self) -> None:
        """Pop removes and returns the final element."""
        values = Uint16List4(data=[Uint16(1), Uint16(2)])
        assert values.pop() == Uint16(2)
        assert values == Uint16List4(data=[Uint16(1)])

    def test_byte_list_setitem_replaces_byte(self) -> None:
        """Byte lists mutate by integer byte value."""
        payload = SmallByteList(data=b"\xde\xad")
        payload[0] = 0xBE
        assert payload == SmallByteList(data=b"\xbe\xad")

    def test_byte_list_append_and_pop(self) -> None:
        """Byte lists append and pop by integer byte value."""
        payload = SmallByteList(data=b"\xde")
        payload.append(0xAD)
        assert payload == SmallByteList(data=b"\xde\xad")
        assert payload.pop() == 0xAD
        assert payload == SmallByteList(data=b"\xde")

    def test_bitlist_append_and_pop(self) -> None:
        """Bitlists append validated bits and pop them back."""
        bits = SmallBitlist(data=[Boolean(True)])
        bits.append(Boolean(False))
        assert bits == SmallBitlist(data=[Boolean(True), Boolean(False)])
        assert bits.pop() == Boolean(False)

    def test_setitem_slice_beyond_limit_rejected(self) -> None:
        """A slice assignment that would exceed the limit fails before storage changes."""
        values = Uint16List4(data=[Uint16(1)])
        with pytest.raises(SSZValueError):
            values[0:1] = [Uint16(2)] * 5
        assert values == Uint16List4(data=[Uint16(1)])

    def test_base_collection_leaves_element_validation_abstract(self) -> None:
        """The shared base defers single-element validation to each family."""
        values = Uint16List4(data=[])
        with pytest.raises(NotImplementedError):
            SSZCollection._validate_element(values, 1)


class TestSSZMutabilityFlag:
    """
    Tests for configuring mutability per type.

    MUTABLE defaults to on and is inherited. A type that sets it to False
    rejects every mutation, while construction and reads keep working.
    """

    def test_immutable_list_rejects_mutation(self) -> None:
        """An immutable list rejects element assignment, append, pop, and data assignment."""

        class FrozenUint16List4(Uint16List4):
            MUTABLE = False

        values = FrozenUint16List4(data=[Uint16(1), Uint16(2)])
        with pytest.raises(SSZTypeError):
            values[0] = Uint16(9)
        with pytest.raises(SSZTypeError):
            values.append(Uint16(3))
        with pytest.raises(SSZTypeError):
            values.pop()
        with pytest.raises(SSZTypeError):
            values.data = [Uint16(9)]
        assert values == FrozenUint16List4(data=[Uint16(1), Uint16(2)])

    def test_immutable_byte_list_rejects_mutation(self) -> None:
        """An immutable byte list rejects byte assignment, append, and pop."""

        class FrozenByteList(SmallByteList):
            MUTABLE = False

        payload = FrozenByteList(data=b"\xde\xad")
        with pytest.raises(SSZTypeError):
            payload[0] = 0xBE
        with pytest.raises(SSZTypeError):
            payload.append(0xEF)
        with pytest.raises(SSZTypeError):
            payload.pop()
        assert payload == FrozenByteList(data=b"\xde\xad")

    def test_immutable_bitlist_rejects_mutation(self) -> None:
        """An immutable bitlist rejects append and pop."""

        class FrozenBitlist(SmallBitlist):
            MUTABLE = False

        bits = FrozenBitlist(data=[Boolean(True)])
        with pytest.raises(SSZTypeError):
            bits.append(Boolean(False))
        with pytest.raises(SSZTypeError):
            bits.pop()

    def test_immutable_container_rejects_field_assignment(self) -> None:
        """An immutable container rejects field assignment while reads keep working."""

        class FrozenContainer(TwoFieldContainer):
            MUTABLE = False

        container = FrozenContainer(x=Uint8(1), y=Uint16(2))
        with pytest.raises(SSZTypeError):
            container.x = Uint8(3)
        assert container.x == Uint8(1)

    def test_mutability_flag_is_inherited(self) -> None:
        """A subclass of an immutable type stays immutable."""

        class FrozenBase(Uint16List4):
            MUTABLE = False

        class StillFrozen(FrozenBase):
            pass

        values = StillFrozen(data=[Uint16(1)])
        with pytest.raises(SSZTypeError):
            values.append(Uint16(2))

    def test_direct_data_assignment_revalidates(self) -> None:
        """Assigning the data field directly runs the same validation as construction."""
        values = Uint16List4(data=[Uint16(1)])
        values.data = cast(Any, [2, 3])
        assert values == Uint16List4(data=[Uint16(2), Uint16(3)])
        with pytest.raises((SSZValueError, ValidationError)):
            values.data = cast(Any, [1, 2, 3, 4, 5])

    def test_container_field_assignment_coerces(self) -> None:
        """Containers are mutable; assigned values coerce into the field type."""
        container = TwoFieldContainer(x=Uint8(1), y=Uint16(2))
        container.x = 3  # ty: ignore[invalid-assignment]
        assert container == TwoFieldContainer(x=Uint8(3), y=Uint16(2))

    def test_container_collection_field_raw_payload_rejected(self) -> None:
        """A raw payload assigned to a collection field fails, exactly as at construction."""
        container = ThreeFieldContainer(a=Uint8(0), b=Uint64(0), c=Uint16List4(data=[]))
        with pytest.raises(ValidationError):
            container.c = [1, 2]  # ty: ignore[invalid-assignment]
        container.c = Uint16List4(data=[Uint16(1), Uint16(2)])
        assert container.c == Uint16List4(data=[Uint16(1), Uint16(2)])

    def test_container_assignment_of_typed_value_passes_through(self) -> None:
        """An already-typed value is assigned without re-coercion."""
        container = TwoFieldContainer(x=Uint8(1), y=Uint16(2))
        container.y = Uint16(9)
        assert container.y == Uint16(9)

    def test_container_unknown_attribute_assignment_raises(self) -> None:
        """Assigning an attribute that is not a field still raises."""
        container = TwoFieldContainer(x=Uint8(1), y=Uint16(2))
        with pytest.raises((AttributeError, ValueError)):
            container.unknown = 1  # ty: ignore[unresolved-attribute]

    def test_container_hashes_by_tree_root(self) -> None:
        """Containers hash by Merkle root, so they work as dict keys."""
        first = TwoFieldContainer(x=Uint8(1), y=Uint16(2))
        second = TwoFieldContainer(x=Uint8(1), y=Uint16(2))
        assert hash(first) == hash(second)
        lookup = {first: "found"}
        assert lookup[second] == "found"
