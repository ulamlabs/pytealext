from pyteal import Tmpl

from pytealext.evaluator import compile_and_run, substitute_template_values


def test_substitute_template_values():
    tmpl = """
    int TMPL_A
    bytes TMPL_B
    +
    -
    addr TMPL_C
    *
    exp
    exp
    exp
    op TMPL_C
    return
    """

    subs = {
        "TMPL_B": "0xaaaaaaaaaabbbbbbbbbbcccccccc00000000fff",
        "TMPL_C": "1234902",
        "TMPL_A": "123123",
    }

    expected = """
    int 123123
    bytes 0xaaaaaaaaaabbbbbbbbbbcccccccc00000000fff
    +
    -
    addr 1234902
    *
    exp
    exp
    exp
    op 1234902
    return
    """

    actual = substitute_template_values(tmpl, subs)
    assert actual == expected


def test_compile_and_run_template():
    program = Tmpl.Int("TMPL_A") + Tmpl.Int("TMPL_B")
    subs = {
        "TMPL_A": "123123",
        "TMPL_B": "555555",
    }
    expected = 678678
    stack, _ = compile_and_run(program, tmpl_subs=subs)

    assert stack == [expected]
