import pytest
from pyteal import Assert, Bytes, For, Int, Return, ScratchVar, Seq

from pytealext import LocalStateArray
from pytealext.evaluator import EvalContext
from pytealext.state import GlobalStateArray2D, LocalStateArray2D

from .helpers import compile_and_run


def test_local_state_array():
    user_counters = LocalStateArray("Counters")
    user_counters_expr = LocalStateArray(Bytes("Counters"))
    i = ScratchVar()
    accumulator = ScratchVar()
    program = Seq(
        user_counters[0].put(Int(10)),
        user_counters[0].add_assign(Int(1)),
        user_counters[0].sub_assign(Int(2)),
        Assert(user_counters[0].get() == Int(9)),
        user_counters_expr[Int(1)].put(Int(9)),
        user_counters_expr[2].put(Int(9)),
        # Indexes can also be accessed with Exprs
        accumulator.store(Int(0)),
        For(i.store(Int(0)), i.load() < Int(3), i.store(i.load() + Int(1))).Do(
            accumulator.store(accumulator.load() + user_counters[i.load()].get())
        ),
        Assert(user_counters_expr[0].get() == Int(9)),
        Return(accumulator.load() == Int(27)),
    )
    ctx = EvalContext()
    stack, slots = compile_and_run(program, context=ctx)
    assert len(stack) == 1
    assert stack[0] == 1


@pytest.mark.parametrize("array_2d_class", [LocalStateArray2D, GlobalStateArray2D])
def test_global_state_array_2D(array_2d_class):
    multiple_users_counters = array_2d_class("Counters")
    multiple_users_counters_expr = array_2d_class(Bytes("Counters"))
    i = ScratchVar()
    j = ScratchVar()
    accumulator = ScratchVar()
    program = Seq(
        multiple_users_counters[0, 0].put(Int(10)),
        multiple_users_counters[0, 0].add_assign(Int(1)),
        multiple_users_counters[0, 0].sub_assign(Int(2)),
        Assert(multiple_users_counters[0, 0].get() == Int(9)),
        multiple_users_counters[Int(0), Int(1)].put(Int(18)),
        multiple_users_counters_expr[Int(1), Int(0)].put(Int(27)),
        multiple_users_counters_expr[Int(1), Int(1)].put(Int(36)),
        # Indexes can also be accessed with Exprs
        accumulator.store(Int(0)),
        For(i.store(Int(0)), i.load() < Int(2), i.store(i.load() + Int(1))).Do(
            For(j.store(Int(0)), j.load() < Int(2), j.store(j.load() + Int(1))).Do(
                accumulator.store(accumulator.load() + multiple_users_counters[i.load(), j.load()].get())
            )
        ),
        Assert(multiple_users_counters[0, 0].get() == Int(9)),
        Return(accumulator.load() == Int(90)),
    )
    ctx = EvalContext()
    stack, slots = compile_and_run(program, context=ctx)
    assert len(stack) == 1
    assert stack[0] == 1
