from hypothesis import assume, example, given
from hypothesis import strategies as st
from pyteal import Int, ScratchVar, Seq

from pytealext import FastExp
from tests.helpers import compile_and_run


@given(
    base=st.integers(min_value=0, max_value=2**10),
    exponent=st.integers(min_value=0, max_value=255),
)
@example(base=0, exponent=0)
@example(base=0, exponent=2**64 - 1)
@example(base=1, exponent=2**64 - 1)
@example(base=2**64 - 1, exponent=0)
@example(base=1000000007, exponent=0)
@example(base=1000000007, exponent=1)
@example(base=1000000007, exponent=2)
@example(base=1000000007, exponent=3)
@example(base=1000000007, exponent=4)
@example(base=1000000007, exponent=5)
def test_FastExp(base: int, exponent: int):
    assume(base**exponent < 2**256)
    base_int = Int(base)
    exponent_int = Int(exponent)
    result = ScratchVar(slotId=0)

    expected = base**exponent

    expr = Seq(result.store(FastExp(base_int, exponent_int)), Int(1))

    stack, slots = compile_and_run(expr)

    actual = int.from_bytes(slots[0], "big")

    assert len(stack) == 1
    assert actual == expected
