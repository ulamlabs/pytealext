from pyteal import Expr, If, Int, Return, ScratchVar, Seq, Subroutine, TealType, While

from pytealext.evaluator import compile_and_run


def fib(n: int) -> int:
    prev_prev = 0
    prev = 1

    if n < 2:
        return n

    for _ in range(2, n + 1):
        current = prev + prev_prev
        prev_prev = prev
        prev = current

    return current


@Subroutine(TealType.uint64)
def pyteal_fib(n: Expr) -> Expr:
    prev_prev = ScratchVar()
    prev = ScratchVar()
    current = ScratchVar()
    i = ScratchVar(slotId=222)

    return Seq(
        If(n < Int(2)).Then(Return(n)),
        prev_prev.store(Int(0)),
        prev.store(Int(1)),
        current.store(Int(0)),
        i.store(Int(2)),
        While(i.load() <= n).Do(
            Seq(
                i.store(i.load() + Int(1)),
                current.store(prev.load() + prev_prev.load()),
                prev_prev.store(prev.load()),
                prev.store(current.load()),
            )
        ),
        Return(current.load()),
    )


def test_pyteal_fibonacci():
    for i in range(0, 43):
        stack, slots = compile_and_run(pyteal_fib(Int(i)))

        if i >= 2:
            assert slots[222] == i + 1

        assert len(stack) == 1
        assert stack[0] == fib(i)
