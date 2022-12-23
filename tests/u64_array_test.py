from math import prod

import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import DataObject
from pyteal import Assert, Bytes, Int, ScratchVar, Seq, TealType

from pytealext import Uint64Array
from pytealext.evaluator import compile_and_run

UINT64_MAX = 2**64 - 1


def encode_list(integers: list[int]) -> bytes:  # noqa
    """Encode list of ints into densely packed uint64s."""
    return b"".join(val.to_bytes(8, "big") for val in integers)


@pytest.mark.parametrize("lt", ([], [1], [1, 2], [UINT64_MAX, 2, 3]))
def test_decode_encode_idempotence(lt: list[int]):
    arr = Uint64Array()
    encoded = encode_list(lt)
    program1 = Seq(arr.decode(Bytes(encoded)), arr.encode() == Bytes(encoded))

    stack, _ = compile_and_run(program1)
    assert stack == [1]


@given(
    initial=st.none() | st.lists(st.integers(min_value=0, max_value=UINT64_MAX)),
    extension=st.lists(st.integers(min_value=0, max_value=UINT64_MAX), min_size=1),
)
def test_append(initial: list[int] | None, extension: list[int]):
    arr = Uint64Array()
    encoded_initial = encode_list(initial) if initial else b""
    encoded_extension = encode_list(extension)
    expected = encoded_initial + encoded_extension

    if initial is None:
        initialize_expr = arr.initialize()
    else:
        initialize_expr = arr.decode(Bytes(encoded_initial))

    program = Seq(
        initialize_expr,
        *(arr.append(Int(val)) for val in extension),
        arr.encode() == Bytes(expected),
    )

    stack, _ = compile_and_run(program)
    assert stack == [1]


@given(
    values=st.lists(st.integers(min_value=0, max_value=UINT64_MAX), min_size=1, max_size=64),
)
def test_getitem(values: list[int]):
    arr = Uint64Array()
    encoded = encode_list(values)
    program = Seq(
        arr.decode(Bytes(encoded)),
        *(Assert(arr[Int(i)] == Int(val)) for i, val in enumerate(values)),
        *(Assert(arr[i] == Int(val)) for i, val in enumerate(values)),
        Int(1),
    )

    # just check for no raised exceptions
    compile_and_run(program)


@given(data=st.data())
def test_set(data: DataObject):
    length = data.draw(st.integers(min_value=1, max_value=64))
    values = data.draw(st.lists(st.integers(min_value=0, max_value=UINT64_MAX), min_size=length, max_size=length))
    set_index = data.draw(st.integers(min_value=0, max_value=length - 1))
    new_value = data.draw(st.integers(min_value=0, max_value=UINT64_MAX))

    arr = Uint64Array()
    initial = encode_list(values)
    values[set_index] = new_value
    expected = encode_list(values)
    program = Seq(
        arr.decode(Bytes(initial)),
        arr.set(set_index, Int(new_value)),
        Assert(arr[set_index] == Int(new_value)),
        arr.encode() == Bytes(expected),
    )

    stack, _ = compile_and_run(program)
    assert stack == [1]

    # test with Int index
    program = Seq(
        arr.decode(Bytes(initial)),
        arr.set(Int(set_index), Int(new_value)),
        Assert(arr[set_index] == Int(new_value)),
        arr.encode() == Bytes(expected),
    )

    stack, _ = compile_and_run(program)
    assert stack == [1]


@given(
    st.lists(st.integers(min_value=0, max_value=2**61 - 1), min_size=1, max_size=8),
    st.lists(st.integers(min_value=0, max_value=2**61 - 1), min_size=1, max_size=8),
)
def test_two_independend_arrays(a1: list[int], a2: list[int]):
    res_prod1 = ScratchVar(TealType.bytes, slotId=1)
    res_prod2 = ScratchVar(TealType.bytes, slotId=2)
    res_sum1 = ScratchVar(TealType.uint64, slotId=3)
    res_sum2 = ScratchVar(TealType.uint64, slotId=4)

    A1 = Uint64Array()
    A2 = Uint64Array()
    encoded1 = encode_list(a1)
    encoded2 = encode_list(a2)

    tree = Seq(
        A1.decode(Bytes(encoded1)),
        A2.decode(Bytes(encoded2)),
        res_prod1.store(A1.product_bytes()),
        res_prod2.store(A2.product_bytes()),
        res_sum1.store(A1.sum()),
        res_sum2.store(A2.sum()),
        Int(1),
    )

    expected = [
        prod(a1),
        prod(a2),
        sum(a1),
        sum(a2),
    ]

    _, slots = compile_and_run(tree)

    actual = slots[1:5]
    actual[0] = int.from_bytes(actual[0], "big")
    actual[1] = int.from_bytes(actual[1], "big")
    for i in range(4):
        assert expected[i] == actual[i]


def test_product_bytes_zero_length():
    arr = Uint64Array()
    program = Seq(
        arr.initialize(),
        arr.product_bytes() == Bytes(b"\x00\x00\x00\x00\x00\x00\x00\x01"),
    )

    stack, _ = compile_and_run(program)
    assert stack == [1]
