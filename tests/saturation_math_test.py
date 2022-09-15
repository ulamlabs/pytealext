import pytest
from pyteal import Int

from pytealext.evaluator import compile_and_run
from pytealext.saturation_math import MAX_UINT64, SaturatingAdd, SaturatingSub


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (0, 0, 0),
        (MAX_UINT64 - 1, 1, MAX_UINT64),
        (MAX_UINT64 - 1, 0, MAX_UINT64 - 1),
        (0, MAX_UINT64 - 1, MAX_UINT64 - 1),
        (MAX_UINT64, MAX_UINT64, MAX_UINT64),
    ],
)
def test_SaturatingAdd(a: int, b: int, expected: int):
    stack, _ = compile_and_run(SaturatingAdd(Int(a), Int(b)))
    assert stack[0] == expected


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (0, 0, 0),
        (MAX_UINT64, 1, MAX_UINT64 - 1),
        (MAX_UINT64, 0, MAX_UINT64),
        (0, MAX_UINT64 - 1, 0),
        (MAX_UINT64 - 1, MAX_UINT64, 0),
        (MAX_UINT64, MAX_UINT64, 0),
    ],
)
def test_SaturatingSub(a: int, b: int, expected: int):
    stack, _ = compile_and_run(SaturatingSub(Int(a), Int(b)))
    assert stack[0] == expected
