from pyteal.ast.tmpl import Tmpl
from pyteal import *
import pytealext as calc
from random import randint
import pytest
from hypothesis import assume, given, note, settings, example, strategies as st
from typing import Tuple, Union
import sys

from .evaluator import eval_teal, Panic, AssertionFailed, MAX_INT

u64_strategy = st.integers(min_value=0, max_value=2 ** 64 - 1)
# TEAL version to use for testing
VERSION = 4

def Bool(expr: Expr) -> Expr:
    return Not(Not(expr))

class MulwDivwTemplate:
    def __init__(self):
        self.m1 = "TMPL_M1"
        self.m2 = "TMPL_M2"
        self.d = "TMPL_D"
        expr = calc.MulDiv64(Tmpl.Int(self.m1), Tmpl.Int(self.m2), Tmpl.Int(self.d))
        self.code = compileTeal(expr, Mode.Application, version=VERSION)

    def get_lines(self, m1, m2, d):
        return self.code.replace(self.m1, str(m1)).replace(self.m2, str(m2)).replace(self.d, str(d)).splitlines()

    def check(self, m1, m2, d):
        lines = self.get_lines(m1, m2, d)
        stack, _ = eval_teal(lines)
        assert len(stack) == 1
        actual = stack[0]
        expected = m1 * m2 // d
        assert actual == expected

mulw_divw_template = MulwDivwTemplate()

@settings(deadline=None)
@given(
    m1=st.integers(min_value=0, max_value=2 ** 64 - 1),
    m2=st.integers(min_value=0, max_value=2 ** 64 - 1),
    d=st.integers(min_value=1, max_value=2 ** 64 - 1),
)
@example(m1=845440975373315, m2=7362476843216198217, d=6559227162326473294)
def test_mulw_divw_extra(m1, m2, d):
    assume(m1 * m2 // d < 2 ** 64)
    mulw_divw_template.check(m1, m2, d)


@pytest.mark.parametrize("bound_check", [True, False])
def test_mulw_divw_stacked(bound_check):
    expr = calc.MulDiv64(
        calc.MulDiv64(Int(123456789), Int(987654321), Int(23456789), bound_check),
        calc.MulDiv64(Int(2137), Int(1337), Int(1000), bound_check),
        Int(2000),
        bound_check,
    )
    expected = (123456789 * 987654321 // 23456789) * (2137 * 1337 // 1000) // 2000
    code = compileTeal(expr, Mode.Application, version=VERSION)
    stack, _ = eval_teal(code.splitlines())
    assert len(stack) == 1
    actual = stack[0]
    assert actual == expected


def test_mulw_divw_bound_check():
    with pytest.raises(AssertionFailed):
        mulw_divw_template.check(2 ** 63, 2, 1)
    with pytest.raises(AssertionFailed):
        mulw_divw_template.check(2 ** 63, 2 ** 63, 2 ** 60)


def test_mulw_divw_no_bound_check():
    m1 = 2 ** 64 - 1
    m2 = 2 ** 64 - 1
    d = 2 ** 63 + 1
    expr = calc.MulDiv64(Int(m1), Int(m2), Int(d), check_bounds=False)
    expected = m1 * m2 // d % MAX_INT

    code = compileTeal(expr, Mode.Application, version=VERSION)
    stack, _ = eval_teal(code.splitlines())
    assert len(stack) == 1
    actual = stack[0]
    assert actual == expected


@given(vals=st.lists(st.integers(min_value=0, max_value=2 ** 64 - 1), min_size=2))
def test_lazyand_boolean_equivalence_with_and(vals: list):
    """
    Test if LazyAnd and And produce the same outcomes
    """
    ast_lazy_and = calc.LazyAnd(*[Int(val) for val in vals])
    ast_and = And(*[Int(val) for val in vals])

    # convert to booleans
    ast_lazy_and = Bool(ast_lazy_and)
    ast_and = Bool(ast_and)

    stack_lazy, _ = compile_and_run(ast_lazy_and)
    stack_eager, _ = compile_and_run(ast_and)

    assert len(stack_lazy) == 1
    assert len(stack_eager) == 1

    assert stack_lazy[0] == stack_eager[0]


def compile_and_run(ast: Expr, mode=Mode.Application, version=VERSION) -> Tuple[list, list]:
    compiled = compileTeal(ast, mode, version=version)
    return eval_teal(compiled.splitlines())


@given(vals=st.lists(st.integers(min_value=0, max_value=2 ** 64 - 1).map(Int), min_size=2))
def test_lazyor_boolean_equivalence_with_or(vals: list):
    """
    Test if LazyOr and Or produce the same outcomes
    """
    ast_lazy_or = calc.LazyOr(*vals)
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
    ast = calc.Min(Int(lhs), Int(rhs))
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
        return calc.Min(assemble_ast(lhs), assemble_ast(rhs))

    stack, _ = compile_and_run(assemble_ast(tree))

    assert len(stack) == 1
    assert stack[0] == find_min(tree)


@given(lhs=u64_strategy, rhs=u64_strategy)
def test_max(lhs: int, rhs: int):
    ast = calc.Max(Int(lhs), Int(rhs))
    stack, _ = compile_and_run(ast)

    assert len(stack) == 1
    assert stack[0] == max(lhs, rhs)
