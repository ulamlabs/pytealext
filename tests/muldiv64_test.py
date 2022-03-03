import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st
from pyteal import Expr, Int, Mode, Not, compileTeal
from pyteal.ast.tmpl import Tmpl

from pytealext import MulDiv64
from pytealext.evaluator import INTEGER_SIZE, AssertionFailed, eval_teal

u64_strategy = st.integers(min_value=0, max_value=2**64 - 1)
# TEAL version to use for testing
VERSION = 5


def Bool(expr: Expr) -> Expr:
    return Not(Not(expr))


class MulwDivwTemplate:
    def __init__(self):
        self.m1 = "TMPL_M1"
        self.m2 = "TMPL_M2"
        self.d = "TMPL_D"
        expr = MulDiv64(Tmpl.Int(self.m1), Tmpl.Int(self.m2), Tmpl.Int(self.d))
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
    m1=st.integers(min_value=0, max_value=2**64 - 1),
    m2=st.integers(min_value=0, max_value=2**64 - 1),
    d=st.integers(min_value=1, max_value=2**64 - 1),
)
@example(m1=845440975373315, m2=7362476843216198217, d=6559227162326473294)
def test_mulw_divw_extra(m1, m2, d):
    assume(m1 * m2 // d < 2**64)
    mulw_divw_template.check(m1, m2, d)


@pytest.mark.parametrize("ceiling", [True, False])
def test_mulw_divw_stacked(ceiling):
    expr = MulDiv64(
        MulDiv64(Int(123456789), Int(987654321), Int(23456789), ceiling),
        MulDiv64(Int(2137), Int(1337), Int(1000), ceiling),
        Int(2000),
        ceiling,
    )
    expected = (123456789 * 987654321 // 23456789) * (2137 * 1337 // 1000) // 2000
    if ceiling:
        # calculate ceiling with property floor((x+y-1)/y) == ceil(x/y)
        r1 = (123456789 * 987654321 + 23456789 - 1) // 23456789
        r2 = (2137 * 1337 + 1000 - 1) // 1000
        d = 2000
        expected = (r1 * r2 + d - 1) // d
    code = compileTeal(expr, Mode.Application, version=VERSION)
    stack, _ = eval_teal(code.splitlines())
    assert len(stack) == 1
    actual = stack[0]
    assert actual == expected


def test_mulw_divw_bound_check():
    with pytest.raises(AssertionFailed):
        mulw_divw_template.check(2**63, 2, 1)
    with pytest.raises(AssertionFailed):
        mulw_divw_template.check(2**63, 2**63, 2**60)


muldiv_ceil_template = MulDiv64(Tmpl.Int("TMPL_M1"), Tmpl.Int("TMPL_M2"), Tmpl.Int("TMPL_D"), ceiling=True)
compiled_ceil_template = compileTeal(muldiv_ceil_template, Mode.Application, version=VERSION)


@settings(deadline=None)
@given(
    m1=st.integers(min_value=0, max_value=2**64 - 1),
    m2=st.integers(min_value=0, max_value=2**64 - 1),
    d=st.integers(min_value=1, max_value=2**64 - 1),
)
@example(m1=845440975373315, m2=7362476843216198217, d=6559227162326473294)
def test_muldiv64_ceiling(m1: int, m2: int, d: int):
    expected = m1 * m2 // d
    if m1 * m2 % d != 0:
        expected += 1
    assume(expected < INTEGER_SIZE)
    code = compiled_ceil_template.replace("TMPL_M1", str(m1)).replace("TMPL_M2", str(m2)).replace("TMPL_D", str(d))
    stack, _ = eval_teal(code.splitlines())

    assert len(stack) == 1
    assert stack[0] == expected
