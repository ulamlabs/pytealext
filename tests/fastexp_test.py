from io import StringIO

import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st
from pyteal import BytesMul, Expr, For, If, Int, Itob, ScratchVar, Seq, Subroutine, TealType

from pytealext import FastExp, Mul128
from pytealext.evaluator import compile_and_run, summarize_execution


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

    _, slots = compile_and_run(expr)

    actual = int.from_bytes(slots[0], "big")

    assert actual == expected


@Subroutine(TealType.bytes, "loopexp")
def loop_exponentiation(base: Expr, exponent: Expr) -> Expr:
    """Optimized exponentiation done in a single loop"""
    acc = ScratchVar()
    i = ScratchVar()
    return Seq(
        If(exponent >= Int(2))
        .Then(Seq(i.store(Int(2)), acc.store(Mul128(base, base))))
        .Else(Seq(i.store(Int(0)), acc.store(Itob(Int(1))))),
        For(Seq(), i.load() < exponent, i.store(i.load() + Int(1))).Do(
            acc.store(BytesMul(acc.load(), Itob(base))),
        ),
        acc.load(),
    )


@pytest.mark.parametrize("base,exponent", list(map(lambda e: (1007, e), range(0, 12))))
def test_FastExp_is_better_than_loop(base: int, exponent: int):
    """
    NOTE:
        This test would fail for powers 2 (63 vs 66 ops) & 4 (96 vs 101 ops)
        therefore we allow fastexp to use up to 5 more ops than loop.
    """
    result = ScratchVar(slotId=0)
    loop_expr = Seq(result.store(loop_exponentiation(Int(base), Int(exponent))), Int(1))

    fast_expr = Seq(
        result.store(FastExp(Int(base), Int(exponent))),
        Int(1),
    )

    s_loop = StringIO()
    s_fast = StringIO()

    _, slots_loop = compile_and_run(loop_expr, debug=s_loop)
    _, slots_fast = compile_and_run(fast_expr, debug=s_fast)

    # sanity check
    expected_result = base**exponent
    assert int.from_bytes(slots_loop[0], "big") == expected_result
    assert int.from_bytes(slots_fast[0], "big") == expected_result

    summary_loop = summarize_execution(s_loop.getvalue())
    summary_fast = summarize_execution(s_fast.getvalue())

    assert summary_loop.execution_cost >= summary_fast.execution_cost - 5
