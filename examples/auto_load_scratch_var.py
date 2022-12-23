from pyteal import Expr, For, If, Int, Return, ScratchVar, Seq, Sqrt, Subroutine, TealType

from pytealext import AutoLoadScratchVar


@Subroutine(TealType.uint64)
def sum_of_integers_in_range(start: Expr, end: Expr) -> Expr:
    """Calculate the sum of integers in the range [start, end)"""
    i = AutoLoadScratchVar(TealType.uint64)
    s = AutoLoadScratchVar(TealType.uint64)

    return Seq(
        s.store(Int(0)),
        For(i.store(start), i < end, i.increment()).Do(
            # with regular scratch vars, this would be:
            # s.store(s.load() + i.load())
            s.increment(i)
        ),
        s.load(),
    )


@Subroutine(TealType.uint64)
def sum_of_integers_in_range_inline(start: Expr, end: Expr) -> Expr:
    """Calculate the sum of integers in the range [start, end)"""

    return Seq(
        (s := AutoLoadScratchVar()).store(0),
        For((i := AutoLoadScratchVar()).store(start), i < end, i.increment()).Do(s.increment(i)),
        s.load(),
    )
