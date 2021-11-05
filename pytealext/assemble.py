from typing import Iterable, Union

from pyteal import Expr, Op, TealBlock, TealSimpleBlock, TealOp, CompileOptions


def assemble_step(options: CompileOptions, op: Union[Op, Expr], *args, expr: Expr = None):
    """
    Convert each step of the pseudo-TEAL into blocks
    """
    # if "op" is an Expr, assemble it directly
    if isinstance(op, Expr):
        return op.__teal__(options)
    if op == Op.store:
        return args[0].store().__teal__(options)
    if op == Op.load:
        return args[0].load().__teal__(options)
    return TealBlock.FromOp(options, TealOp(expr=expr, op=op), *args)


def assemble_steps(steps: Iterable[tuple], options: CompileOptions, expr=None) -> tuple[TealBlock, TealSimpleBlock]:
    """
    Assemble steps in pseudo-TEAL into a sequence of blocks
    """
    start = None
    end = None
    for i, step in enumerate(steps):
        argStart, argEnd = assemble_step(options, *step, expr=expr)
        if i == 0:
            start = argStart
            end = argEnd
        else:
            end.setNextBlock(argStart)
            end = argEnd

    return start, end

def new_assembler(steps: Iterable[TealOp or Expr], options: CompileOptions) -> tuple[TealBlock, TealSimpleBlock]:
    """
    Assemble steps that are either expressions or TEALOps into a sequence of blocks
    """
    start = None
    end = None
    for i, step in enumerate(steps):
        if isinstance(step, Expr):
            argStart, argEnd = step.__teal__(options)
        else:
            argStart, argEnd = TealBlock.FromOp(options, step)
        if i == 0:
            start = argStart
            end = argEnd
        else:
            end.setNextBlock(argStart)
            end = argEnd

    return start, end
