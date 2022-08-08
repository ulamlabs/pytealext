from pyteal import MAX_PROGRAM_VERSION, Expr, Mode, compileTeal

from .evaluator import eval_teal


def compile_and_run(
    ast: Expr, mode=Mode.Application, version=MAX_PROGRAM_VERSION, *, context=None, debug=None
) -> tuple[list[bytes or int], list[bytes or int]]:
    """Compile the given AST and run it using eval_teal"""
    compiled = compileTeal(ast, mode, version=version)
    return eval_teal(compiled.splitlines(), context=context, debug=debug)
