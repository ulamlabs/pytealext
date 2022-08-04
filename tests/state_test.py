import pytest
from pyteal import App, Assert, Bytes, For, Int, Not, Return, ScratchVar, Seq

from pytealext.evaluator import EvalContext
from pytealext.state import (
    GlobalState,
    GlobalStateArray2D,
    LocalState,
    LocalStateArray,
    LocalStateArray2D,
)

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
    stack, _ = compile_and_run(program, context=ctx)
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
    stack, _ = compile_and_run(program, context=ctx)
    assert len(stack) == 1
    assert stack[0] == 1


@pytest.mark.parametrize(
    "key,val",
    [
        ("aaa", 123),
        ("bbb", 456),
        ("ccc", b"sugoma"),
    ],
)
def test_local_get_ex(key: str, val: bytes or int):
    ls = LocalState(key)
    if isinstance(val, bytes):
        val = Bytes(val)
    else:
        val = Int(val)
    local_get_ex_expr = Seq(
        ls.put(val),
        ex := App.localGetEx(Int(0), Int(0), Bytes(key)),
        Assert(ex.hasValue()),
        Return(ls.get() == ex.value()),
    )
    ctx = EvalContext()
    stack, _ = compile_and_run(local_get_ex_expr, context=ctx)
    assert stack == [1]


@pytest.mark.parametrize(
    "key,val",
    [
        ("aaa", 123),
        ("bbb", 456),
        ("ccc", b"sugoma"),
    ],
)
def test_global_get_ex(key: str, val: bytes or int):
    gs = GlobalState(key)
    if isinstance(val, bytes):
        val = Bytes(val)
    else:
        val = Int(val)
    global_get_ex_expr = Seq(
        gs.put(val),
        ex := App.globalGetEx(Int(0), Bytes(key)),
        Assert(ex.hasValue()),
        Return(gs.get() == ex.value()),
    )
    ctx = EvalContext()
    stack, _ = compile_and_run(global_get_ex_expr, context=ctx)
    assert stack == [1]


def test_state_exists():
    ls = LocalState("aaa")
    gs = GlobalState("bbb")

    program = Seq(
        Assert(Not(ls.exists())),
        Assert(Not(gs.exists())),
        Assert(Not(ls.exists())),
        ls.put(Int(123)),
        Assert(ls.exists()),
        Assert(Not(gs.exists())),
        gs.put(Int(123)),
        Assert(gs.exists()),
        Return(Int(1)),
    )

    ctx = EvalContext()
    stack, _ = compile_and_run(program, context=ctx)

    assert stack == [1]
