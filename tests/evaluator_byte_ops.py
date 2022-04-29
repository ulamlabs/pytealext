from math import isqrt
from typing import Callable

import pytest
from hypothesis import given, assume
from hypothesis import strategies as st
from pyteal import (
    compileTeal,
    Mode,
    BytesAdd,
    BytesMinus,
    BytesDiv,
    BytesMul,
    BytesEq,
    Bytes,
    Itob,
    Int,
    BytesSqrt,
)

from pytealext.evaluator.evaluator import (
    int_to_trimmed_bytes,
    Panic,
    eval_teal,
    EvalContext,
)

VERSION = 6


@pytest.mark.parametrize("function", (BytesAdd, BytesMinus, BytesDiv, BytesMul))
def test_ops_fail_for_overflows(function: Callable):
    large_bytes = Bytes(int_to_trimmed_bytes(2 ** 512))

    expr = compileTeal(
        BytesEq(function(large_bytes, large_bytes), Itob(Int(1))),
        Mode.Application,
        version=VERSION,
    )

    with pytest.raises(Panic, match="Bytes overflow"):
        eval_teal(expr.splitlines(), context=EvalContext())


@given(
    i=st.integers(min_value=1, max_value=2 ** 255),
)
def test_trimming_bytes(i: int):
    i_bytes = int_to_trimmed_bytes(i)

    assert int.from_bytes(i_bytes, "big") == i
    assert i_bytes[0] != 0


@given(
    i=st.integers(min_value=1, max_value=2 ** 255),
    j=st.integers(min_value=1, max_value=2 ** 255),
)
def test_bytes_add(i: int, j: int):
    i_bytes = Bytes(int_to_trimmed_bytes(i))
    j_bytes = Bytes(int_to_trimmed_bytes(j))

    expected = Bytes(int_to_trimmed_bytes(i + j))

    expr = BytesEq(BytesAdd(i_bytes, j_bytes), expected)
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    stack, _ = eval_teal(expr_asm.splitlines())

    assert len(stack) == 1
    assert stack[0] == 1


@given(
    i=st.integers(min_value=1, max_value=2 ** 255),
    j=st.integers(min_value=1, max_value=2 ** 255),
)
def test_bytes_minus(i: int, j: int):
    assume(i > j)
    i_bytes = Bytes(int_to_trimmed_bytes(i))
    j_bytes = Bytes(int_to_trimmed_bytes(j))

    expected = Bytes(int_to_trimmed_bytes(i - j))

    expr = BytesEq(BytesMinus(i_bytes, j_bytes), expected)
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    stack, _ = eval_teal(expr_asm.splitlines())

    assert len(stack) == 1
    assert stack[0] == 1


@given(
    i=st.integers(min_value=1, max_value=2 ** 255),
    j=st.integers(min_value=1, max_value=2 ** 255),
)
def test_bytes_minus_fails_for_underflow(i: int, j: int):
    assume(i < j)
    i_bytes = Bytes(int_to_trimmed_bytes(i))
    j_bytes = Bytes(int_to_trimmed_bytes(j))

    expr = BytesEq(BytesMinus(i_bytes, j_bytes), Itob(Int(1)))
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    with pytest.raises(Panic, match="Underflow"):
        eval_teal(expr_asm.splitlines(), context=EvalContext())


@given(
    i=st.integers(min_value=1, max_value=2 ** 255),
    j=st.integers(min_value=1, max_value=2 ** 255),
)
def test_bytes_div(i: int, j: int):
    assume(i > j)
    i_bytes = Bytes(int_to_trimmed_bytes(i))
    j_bytes = Bytes(int_to_trimmed_bytes(j))

    expected = Bytes(int_to_trimmed_bytes(i // j))

    expr = BytesEq(BytesDiv(i_bytes, j_bytes), expected)
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    stack, _ = eval_teal(expr_asm.splitlines())

    assert len(stack) == 1
    assert stack[0] == 1


@given(i=st.integers(min_value=1, max_value=2 * 255))
def test_bytes_div_fails_for_illegal_division(i: int):
    zero = Itob(Int(0))
    i_bytes = Bytes(int_to_trimmed_bytes(i))

    expr = BytesEq(BytesDiv(i_bytes, zero), Bytes(b""))
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    with pytest.raises(Panic, match="Division by 0"):
        eval_teal(expr_asm.splitlines(), context=EvalContext())


@given(
    i=st.integers(min_value=1, max_value=2 ** 255),
    j=st.integers(min_value=1, max_value=2 ** 255),
)
def test_bytes_mul(i: int, j: int):
    i_bytes = Bytes(int_to_trimmed_bytes(i))
    j_bytes = Bytes(int_to_trimmed_bytes(j))

    expected = Bytes(int_to_trimmed_bytes(i * j))

    expr = BytesEq(BytesMul(i_bytes, j_bytes), expected)
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    stack, _ = eval_teal(expr_asm.splitlines())

    assert len(stack) == 1
    assert stack[0] == 1


@given(
    i=st.integers(min_value=1, max_value=2 ** 255),
)
def test_bytes_sqrt(i: int):
    i_bytes = Bytes(int_to_trimmed_bytes(i))

    expected = Bytes(int_to_trimmed_bytes(isqrt(i)))

    expr = BytesEq(BytesSqrt(i_bytes), expected)
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    stack, _ = eval_teal(expr_asm.splitlines())

    assert len(stack) == 1
    assert stack[0] == 1
