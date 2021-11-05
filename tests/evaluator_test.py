from hypothesis import given
from hypothesis import strategies as st
from pyteal import Btoi, Bytes, Int, Itob, Log, Mode, Pop, Seq, compileTeal

from pytealext.evaluator import eval_teal
from pytealext.evaluator.evaluator import EvalContext

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
    assert stack[0] == int.from_bytes(b, "big")


def test_log():
    expr = Seq(Log(Bytes(b"wubwub")), Pop(Int(1000)), Log(Bytes("numbertwo")), Int(1))
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    ctx = EvalContext()
    stack, _ = eval_teal(expr_asm.splitlines(), context=ctx)

    assert stack == [1]
    assert ctx.log == [b"wubwub", b"numbertwo"]

def test_equals():
    expr_ok = Int(10) == Int(10)
    expr_bad = Int(10) == Int(11)
    expr_ok_b = Bytes(b"wub") == Bytes(b"wub")
    expr_bad_b = Bytes(b"wub") == Bytes(b"wubwub")

    expr_ok_asm = compileTeal(expr_ok, Mode.Application, version=VERSION)
    expr_bad_asm = compileTeal(expr_bad, Mode.Application, version=VERSION)
    expr_ok_b_asm = compileTeal(expr_ok_b, Mode.Application, version=VERSION)
    expr_bad_b_asm = compileTeal(expr_bad_b, Mode.Application, version=VERSION)

    stack, _ = eval_teal(expr_ok_asm.splitlines())
    assert stack == [1]
    stack, _ = eval_teal(expr_bad_asm.splitlines())
    assert stack == [0]
    stack, _ = eval_teal(expr_ok_b_asm.splitlines())
    assert stack == [1]
    stack, _ = eval_teal(expr_bad_b_asm.splitlines())
    assert stack == [0]
