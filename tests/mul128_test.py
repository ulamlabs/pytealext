from hypothesis import example, given, settings
from hypothesis import strategies as st
from pyteal import Int, Mode, ScratchVar, Seq, TealType

from pytealext.evaluator import compile_and_run
from pytealext.mul128 import Mul128

VERSION = 6
MAX_UINT64 = 2**64 - 1


@given(
    st.integers(min_value=0, max_value=MAX_UINT64),
    st.integers(min_value=0, max_value=MAX_UINT64),
)
@settings(max_examples=100)
@example(0, 0)
@example(MAX_UINT64, MAX_UINT64)
def test_mul128(a: int, b: int):
    res = ScratchVar(TealType.bytes, slotId=1)
    expected = a * b
    expr = Seq(res.store(Mul128(Int(a), Int(b))), Int(1))
    actual = compile_and_run(expr, mode=Mode.Application, version=VERSION)[1][1]
    actual = int.from_bytes(actual, "big")
    assert actual == expected
