from pyteal import Expr, Mode, compileTeal

from pytealext.evaluator import eval_teal

VERSION = 5


def compile_and_run(ast: Expr, mode=Mode.Application, version=VERSION, *, context=None) -> tuple[list, list]:
    compiled = compileTeal(ast, mode, version=version)
    return eval_teal(compiled.splitlines(), context=context)
