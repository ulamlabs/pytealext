from typing import cast

from hypothesis import given
from hypothesis import strategies as st
from pyteal import Bytes, Int, ScratchVar, Seq, TealType

from pytealext import BytesMax, BytesMin
from pytealext.evaluator import compile_and_run


@given(
    lhs=st.binary(max_size=64),
    rhs=st.binary(max_size=64),
)
def test_bytes_min_max(lhs, rhs):
    mini = ScratchVar(TealType.bytes, slotId=1)
    maxi = ScratchVar(TealType.bytes, slotId=2)
    ast = Seq(
        mini.store(BytesMin(Bytes(lhs), Bytes(rhs))),
        maxi.store(BytesMax(Bytes(lhs), Bytes(rhs))),
        Int(1),
    )

    stack, slots = compile_and_run(ast)

    lhs = int.from_bytes(lhs, byteorder="big")  # type: ignore
    rhs = int.from_bytes(rhs, byteorder="big")  # tpye: ignore
    expected_min = min(lhs, rhs)
    expected_max = max(lhs, rhs)

    assert stack == [1]
    assert int.from_bytes(cast(bytes, slots[1]), "big") == expected_min
    assert int.from_bytes(cast(bytes, slots[2]), "big") == expected_max
