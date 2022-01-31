from pyteal import Assert, Int, Seq, For, ScratchVar, Return
from pytealext import LocalStateArray

user_counters = LocalStateArray("Counters")
i = ScratchVar()
accumulator = ScratchVar()
program = Seq(
    user_counters[0].put(Int(10)),
    user_counters[0].add_assign(Int(1)),
    user_counters[0].sub_assign(Int(2)),
    Assert(user_counters[0].get() == Int(9)),
    user_counters[1].put(Int(9)),
    user_counters[2].put(Int(9)),
    # Indexes can also be accessed with Exprs
    For(i.store(Int(0)), i < Int(3), i.store(i.load() + Int(1))).Do(
        accumulator.store(accumulator.load() + user_counters[i.load()].get())
    ),
    Return(accumulator.load() == Int(27))
)