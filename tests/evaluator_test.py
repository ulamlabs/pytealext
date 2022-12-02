import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from pyteal import (
    And,
    App,
    Btoi,
    Bytes,
    Eq,
    Exp,
    Extract,
    ExtractUint16,
    ExtractUint32,
    ExtractUint64,
    Int,
    Itob,
    Log,
    Mode,
    Pop,
    Replace,
    Seq,
    compileTeal,
)

from pytealext.evaluator import EvalContext, Panic, compile_and_run, eval_teal

VERSION = 7


@given(
    i=st.integers(min_value=0, max_value=2**64 - 1),
)
def test_itob_btoi_idempotency(i: int):
    expr = Btoi(Itob(Int(i)))
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    stack, _ = eval_teal(expr_asm)

    assert len(stack) == 1
    assert stack[0] == i


@given(
    b=st.binary(min_size=0, max_size=8),
)
def test_btoi(b: bytes):
    expr = Btoi(Bytes(b))
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    stack, _ = eval_teal(expr_asm)

    assert len(stack) == 1
    assert stack[0] == int.from_bytes(b, "big")


def test_log():
    expr = Seq(Log(Bytes(b"wubwub")), Pop(Int(1000)), Log(Bytes("numbertwo")), Int(1))
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    ctx = EvalContext()
    stack, _ = eval_teal(expr_asm, context=ctx)

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


def test_math_ops_fail_with_byte_type():
    ops = ["addw", "mulw", "/", "%", "+", "-", "*", "&&", "||", ">", "<"]
    bad_programs = [
        ["byte 0x01", "byte 0x02"],
        ["byte 0x03", "int 4"],
        ["int 5", "byte 0x06"],
    ]
    for op in ops:
        for bad_program in bad_programs:
            bp = bad_program + [op]
            with pytest.raises(Panic, match="Invalid type"):
                eval_teal(bp)


def test_int_out_of_range_int_fails():
    programs = [[f"int {2**64}"], ["int -1"]]
    for program in programs:
        with pytest.raises(Panic):
            eval_teal(program)


def test_extract_uint():
    raw_bytes = b"1234567890,./[]123sdf[vl"

    extract_functions = [
        (ExtractUint16, 2),
        (ExtractUint32, 4),
        (ExtractUint64, 8),
    ]

    for ExtractUint, width in extract_functions:
        test_program = Seq(
            ExtractUint(Bytes(raw_bytes), Int(7)) == Btoi(Bytes(raw_bytes[7 : 7 + width])),
        )

        stack, _ = compile_and_run(test_program)

        assert len(stack) == 1
        assert stack[0] == 1


def test_extract():
    raw_bytes = b" ,./l;'p[]90-0-=zxcvhfjrituy"

    test_program = Extract(Bytes(raw_bytes), Int(3), Int(10)) == Bytes(raw_bytes[3 : 3 + 10])

    stack, _ = compile_and_run(test_program)

    assert len(stack) == 1
    assert stack[0] == 1


def test_local_state():
    mapping = {
        b"0": 0,
        b"1": 1,
        b"2": 2,
        b"3": 3,
        b"4": 4,
        b"5": 5,
        b"6": 6,
        b"7": 7,
        b"8": 8,
        b"9": 923409342890234890,
        b"a": b"a",
        b"b": b"b",
        b"c": b"c",
        b"d": b"d",
        b"e": b"e",
        b"f": b"f",
    }

    program = Seq(
        *[
            App.localPut(
                Int(0),
                Bytes(key),
                (Bytes(value) if isinstance(value, bytes) else Int(value)),
            )
            for key, value in mapping.items()
        ],
        And(
            *[
                App.localGet(Int(0), Bytes(key)) == (Bytes(value) if isinstance(value, bytes) else Int(value))
                for key, value in mapping.items()
            ]
        ),
    )

    ctx = EvalContext()

    compiled = compileTeal(program, Mode.Application, version=VERSION)

    stack, _ = eval_teal(compiled.splitlines(), context=ctx)

    assert len(stack) == 1
    assert stack[0] == 1

    for k, v in mapping.items():
        assert ctx.local_state[k] == v


@given(
    i=st.integers(min_value=0, max_value=2**10),
    j=st.integers(min_value=1, max_value=64),
)
def test_exp(i: int, j: int):
    assume(i**j <= 2**64 - 1)
    i_int = Int(i)
    j_int = Int(j)

    expected = Int(i**j)

    expr = Eq(Exp(i_int, j_int), expected)
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    stack, _ = eval_teal(expr_asm)

    assert len(stack) == 1
    assert stack[0] == 1


@pytest.mark.parametrize("base", [1, 2, 1000000007, 2**64 - 1])
def test_exp_zero_exponent(base: int):
    expr = Eq(Exp(Int(base), Int(0)), Int(1))
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    stack, _ = eval_teal(expr_asm)

    assert len(stack) == 1
    assert stack[0] == 1


def test_exp_fails_for_zeroes():
    i_int = Int(0)
    j_int = Int(0)

    expr = Eq(Exp(i_int, j_int), Int(1))
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    with pytest.raises(Panic, match="Invalid input"):
        eval_teal(expr_asm)


@given(
    i=st.integers(min_value=2**62, max_value=2**64 - 1),
    j=st.integers(min_value=2**5, max_value=2**8),
)
def test_exp_fails_for_overflow(i: int, j: int):
    i_int = Int(i)
    j_int = Int(j)

    expr = Eq(Exp(i_int, j_int), Int(1))
    expr_asm = compileTeal(expr, Mode.Application, version=VERSION)

    with pytest.raises(Panic, match="Overflow"):
        eval_teal(expr_asm)


@pytest.mark.parametrize(
    "string,start,replacement,expected",
    (
        ("", 0, "", ""),
        ("b", 0, "a", "a"),
        ("Hello, World!", 7, "devil", "Hello, devil!"),
        ("Hello, World!", 5, "", "Hello, World!"),
    ),
)
def test_replace(string: str, start: int, replacement: str, expected: str):
    program_rep2 = Replace(Bytes(string), Int(start), Bytes(replacement)) == Bytes(expected)
    program_rep2 = compileTeal(program_rep2, Mode.Application, version=VERSION)
    # check that we are really testing replace2
    assert "replace2" in program_rep2

    stack, _ = eval_teal(program_rep2.splitlines())
    assert stack == [1]

    program_rep3 = Replace(Bytes(string), Int(start) + Int(0), Bytes(replacement)) == Bytes(expected)
    program_rep3 = compileTeal(program_rep3, Mode.Application, version=VERSION)
    # check that we are really testing replace3
    assert "replace3" in program_rep3

    stack, _ = eval_teal(program_rep3.splitlines())
    assert stack == [1]
