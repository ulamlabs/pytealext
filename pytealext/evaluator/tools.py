import re
from typing import IO

from pyteal import MAX_PROGRAM_VERSION, Expr, Mode, compileTeal

from .evaluator import EvalContext, eval_teal


def substitute_template_values(teal: str, substitutions: dict[str, str]) -> str:
    """Replaces all template variables (those starting with `TMPL_`)"""

    def repl(m: re.Match) -> str:
        return substitutions.get(m[0], m[0])

    return re.sub(r"\bTMPL_\w+\b", repl, teal)


def compile_and_run(
    ast: Expr,
    mode: Mode = Mode.Application,
    *,
    version: int = MAX_PROGRAM_VERSION,
    context: EvalContext = None,
    debug: IO = None,
    tmpl_subs: dict[str, str] = None
) -> tuple[list[bytes or int], list[bytes or int]]:
    """Compile the given AST and run it using eval_teal

    Should the given AST contain any Tmpl expressions,
    it is necessary to pass in a dictionary of substitutions for such expressions.

    Example program adding two integers:
        ```python
        program = (Tmpl.Int("TMPL_A") + Tmpl.Int("TMPL_B"))

        # two substitutions must be provided (note that all of the values must be strings)
        tmpl_subs = {
            "TMPL_A": "1",
            "TMPL_B": "2"
        }

        stack, _ = compile_and_run(program, tmpl_subs=tmpl_subs)

        assert stack[0] == 3
        ```

    Note: The code must not use any strings that contain the substring `TMPL_` as they might get replaced.

    Args:
        ast: The PyTEAL AST to compile and run
        mode: The compiler mode to use
        version: TEAL version
        context: instance of EvalContext (required when using global state)
        debug: IO object to write execution log to
        tmpl_subs: dict of template substitutions
    """
    compiled = compileTeal(ast, mode, version=version)
    if tmpl_subs is not None:
        compiled = substitute_template_values(compiled, tmpl_subs)
    return eval_teal(compiled.splitlines(), context=context, debug=debug)
