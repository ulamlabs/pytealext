import pytest
from hypothesis import given, note
from hypothesis import strategies as st
from pyteal import Approve, Bytes, Int, Mode, ScratchSlot, Seq, compileTeal

from pytealext.evaluator import Panic, eval_teal
from pytealext.serialize import DeserializeIntegers, DeserializeIntegersToSlots, SerializeIntegers


@given(
    ints=st.lists(st.integers(0, 2**64 - 1), min_size=1, max_size=24),  #
    width=st.just(64) | st.just(32) | st.just(16),
)
def test_serialize_integers(ints: list[int], width: int):
    byte = ScratchSlot(0)
    expr = Seq(byte.store(SerializeIntegers(*[Int(i) for i in ints], width=width)), Approve())
    expr_asm = compileTeal(expr, Mode.Application, version=5)

    _, slots = eval_teal(expr_asm.splitlines())

    byte_width = width // 8
    expected = b"".join([i.to_bytes(8, "big")[8 - byte_width :] for i in ints])

    assert slots[0] == expected


@given(
    ints=st.lists(st.integers(0, 2**64 - 1), min_size=1, max_size=24),  #
    width=st.just(64) | st.just(32) | st.just(16),
)
def test_serialize_deserialize_idempotency(ints: list[int], width: int):
    # trimm the numbers to the width so that the functions are truly idempotent
    ints = [i % 2**width for i in ints]

    byte = ScratchSlot(255)
    deserialized_integers = [ScratchSlot(i) for i in range(len(ints))]
    expr = Seq(
        byte.store(SerializeIntegers(*[Int(i) for i in ints], width=width)),
        *[deserialized_integers[i].store(DeserializeIntegers(byte.load(), width=width)[i]) for i in range(len(ints))],
        Approve()
    )
    expr_asm = compileTeal(expr, Mode.Application, version=5)

    _, slots = eval_teal(expr_asm.splitlines())
    note(slots)

    for actual, expected in zip(slots[: len(ints)], ints):
        assert actual == expected


@given(
    ints=st.lists(st.integers(0, 2**64 - 1), min_size=1, max_size=24),  #
    width=st.just(64) | st.just(32) | st.just(16),
)
def test_serialize_deserialize_to_slots_idempotency(ints: list[int], width: int):
    # trimm the numbers to the width so that the functions are truly idempotent
    ints = [i % 2**width for i in ints]

    byte = ScratchSlot(255)
    deserialized_integers = [ScratchSlot(i) for i in range(len(ints))]
    expr = Seq(
        byte.store(SerializeIntegers(*[Int(i) for i in ints], width=width)),
        DeserializeIntegersToSlots(byte.load(), *deserialized_integers, width=width),
        Approve(),
    )
    expr_asm = compileTeal(expr, Mode.Application, version=5)

    _, slots = eval_teal(expr_asm.splitlines())
    note(slots)

    for actual, expected in zip(slots[: len(ints)], ints):
        assert actual == expected
