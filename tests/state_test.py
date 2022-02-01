from pyteal import Assert, Bytes, For, Int, Return, ScratchVar, Seq

from pytealext import LocalStateArray
from pytealext.evaluator import EvalContext

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
