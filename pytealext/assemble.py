from typing import Iterable

from pyteal import CompileOptions, Expr, TealBlock, TealOp, TealSimpleBlock


def assemble_steps(steps: Iterable[TealOp | Expr], options: CompileOptions) -> tuple[TealBlock, TealSimpleBlock]:
    """
    Assemble steps that are either expressions or TEALOps into a sequence of blocks
    """
    end: TealSimpleBlock = TealSimpleBlock([])
    start: TealBlock = end
    for step in steps:
        if isinstance(step, Expr):
            argStart, argEnd = step.__teal__(options)
        elif isinstance(step, TealOp):
            argStart, argEnd = TealBlock.FromOp(options, step)
        else:
            raise TypeError(f"Expected Expr or TealOp, got {type(step)}")
        end.setNextBlock(argStart)
        end = argEnd

    return start, end
