import os
import sys
from hypothesis import given, settings, example
from hypothesis.strategies import integers

from pyteal import (
    Int,
    ScratchVar,
    TealType,
    Mode,
    Seq,
)

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
THIS_DIR = os.path.dirname(os.path.realpath(THIS_DIR))
sys.path.insert(1, THIS_DIR)

from pytealext.mul128 import Mul128

from tests.helpers import compile_and_run


VERSION = 6
MAX_UINT64 = 2 ** 64 - 1



@given(integers(min_value=0, max_value=MAX_UINT64), integers(min_value=0, max_value=MAX_UINT64))
@settings(max_examples=100)
@example(0,0)
@example(MAX_UINT64, MAX_UINT64)
def test_mul128(a: int, b: int):
    res = ScratchVar(TealType.bytes, slotId=1)
    expected = a*b
    actual = compile_and_run(Seq(res.store(Mul128(Int(a), Int(b))), Int(1)), mode=Mode.Application, version=VERSION)[1][1]
    actual = int.from_bytes(actual, "big")
    assert actual == expected
