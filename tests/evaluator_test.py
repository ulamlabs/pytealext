from hypothesis import given
from hypothesis import strategies as st
from pyteal import Btoi, Int, Itob, Mode, compileTeal, Bytes

from pytealext.evaluator import eval_teal

VERSION = 5


@given(
    i=st.integers(min_value=0, max_value=2 ** 64 - 1),
)
def test_itob_btoi_idempotency(i: int):
    expr = Btoi(Itob(Int(i)))
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    stack, _ = eval_teal(expr_asm.splitlines())

    assert len(stack) == 1
    assert stack[0] == i

@given(
    b=st.binary(min_size=0, max_size=8),
)
def test_btoi(b: bytes):
    expr = Btoi(Bytes(b))
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    stack, _ = eval_teal(expr_asm.splitlines())

    assert len(stack) == 1
    assert stack[0] == int.from_bytes(b, 'big')
