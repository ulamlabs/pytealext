from typing import Tuple, Union

from hypothesis import assume, given
from hypothesis import strategies as st
from pyteal import And, Expr, Int, Mode, Not, Or, compileTeal

from pytealext import LazyAnd, LazyOr, Max, Min
from pytealext.evaluator import eval_teal
from tests.helpers import compile_and_run

u64_strategy = st.integers(min_value=0, max_value=2**64 - 1)
# TEAL version to use for testing
VERSION = 4


def Bool(expr: Expr) -> Expr:
    return Not(Not(expr))


@given(vals=st.lists(st.integers(min_value=0, max_value=2**64 - 1), min_size=2))
def test_lazyand_boolean_equivalence_with_and(vals: list):
    """
    Test if LazyAnd and And produce the same outcomes
    """
    ast_lazy_and = LazyAnd(*[Int(val) for val in vals])
    ast_and = And(*[Int(val) for val in vals])

    # convert to booleans
    ast_lazy_and = Bool(ast_lazy_and)
    ast_and = Bool(ast_and)

    stack_lazy, _ = compile_and_run(ast_lazy_and)
    stack_eager, _ = compile_and_run(ast_and)

    assert len(stack_lazy) == 1
    assert len(stack_eager) == 1

    assert stack_lazy[0] == stack_eager[0]


@given(vals=st.lists(st.integers(min_value=0, max_value=2**64 - 1).map(Int), min_size=2))
def test_lazyor_boolean_equivalence_with_or(vals: list):
    """
    Test if LazyOr and Or produce the same outcomes
    """
    ast_lazy_or = LazyOr(*vals)
    ast_or = Or(*vals)

    # convert to booleans
    ast_lazy_or = Bool(ast_lazy_or)
    ast_or = Bool(ast_or)

    stack_lazy, _ = compile_and_run(ast_lazy_or)
    stack_eager, _ = compile_and_run(ast_or)

    assert len(stack_lazy) == 1
    assert len(stack_eager) == 1

    assert stack_lazy[0] == stack_eager[0]


@given(lhs=u64_strategy, rhs=u64_strategy)
def test_min(lhs: int, rhs: int):
    ast = Min(Int(lhs), Int(rhs))
    stack, _ = compile_and_run(ast)

    assert len(stack) == 1
    assert stack[0] == min(lhs, rhs)


@given(tree=st.recursive(u64_strategy, lambda children: st.tuples(children, children)))
def test_min_recursive(tree: Expr):
    """
    Fun experiment with generating random trees of Min
    """
    assume(isinstance(tree, tuple))

    def find_min(node: Union[tuple, int]) -> int:
        if isinstance(node, int):
            return node
        return min(find_min(node[0]), find_min(node[1]))

    def assemble_ast(node: Union[tuple, int]) -> Expr:
        if isinstance(node, int):
            return Int(node)
        lhs, rhs = node
        return Min(assemble_ast(lhs), assemble_ast(rhs))

    stack, _ = compile_and_run(assemble_ast(tree))

    assert len(stack) == 1
    assert stack[0] == find_min(tree)


@given(lhs=u64_strategy, rhs=u64_strategy)
def test_max(lhs: int, rhs: int):
    ast = Max(Int(lhs), Int(rhs))
    stack, _ = compile_and_run(ast)

    assert len(stack) == 1
    assert stack[0] == max(lhs, rhs)
