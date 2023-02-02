import pytest
from pyteal import Bytes, Expr, Int, ScratchVar, Seq, Subroutine, TealInputError, TealType

from examples.auto_load_scratch_var import sum_of_integers_in_range, sum_of_integers_in_range_inline
from pytealext import AutoLoadScratchVar
from pytealext.evaluator import compile_and_run


def test_AutoLoadScratchVar():
    i = AutoLoadScratchVar(TealType.uint64)
    s = AutoLoadScratchVar(TealType.uint64)

    program = sum_of_integers_in_range(Int(0), Int(10))
    program_2 = sum_of_integers_in_range_inline(Int(0), Int(10))

    stack, _ = compile_and_run(program)
    stack_2, _ = compile_and_run(program_2)
    assert stack[0] == 45
    assert stack_2[0] == 45


@pytest.mark.parametrize(
    "source,expected",
    [(Int(1123), 1123), (Bytes("hello"), b"hello"), (123123, 123123), (b"hello\x00", b"hello\x00"), ("'sup", b"'sup")],
)
def test_store_different_types(source, expected):
    s = AutoLoadScratchVar(slotId=10)
    program = Seq(s.store(source), Int(1))

    _, slots = compile_and_run(program)
    assert slots[10] == expected


@pytest.mark.parametrize(
    "amt",
    [
        0,
        1,
        500,
        1000,
    ],
)
def test_increment(amt: int):
    s = AutoLoadScratchVar()
    program = Seq(s.store(1000), s.increment(amt), s.load())

    stack, _ = compile_and_run(program)
    assert stack[0] == 1000 + amt


@pytest.mark.parametrize(
    "amt",
    [
        0,
        1,
        500,
        1000,
    ],
)
def test_decrement(amt: int):
    s = AutoLoadScratchVar()
    program = Seq(s.store(1000), s.decrement(amt), s.load())

    stack, _ = compile_and_run(program)
    assert stack[0] == 1000 - amt


def test_ALSV_cannot_be_an_argument_to_subroutine():
    with pytest.raises(TealInputError, match="Function has parameter s of disallowed type"):

        @Subroutine(TealType.uint64)
        def increment(s: AutoLoadScratchVar) -> Expr:
            return s.increment(1)


def test_ALSV_cannot_be_passed_as_scratch_var():
    @Subroutine(TealType.uint64)
    def increment(s: ScratchVar) -> Expr:
        return s.store(s.load() + Int(1))

    with pytest.raises(TealInputError, match=r"supplied argument .*? at index 0 had type .*? but was expecting type"):
        program = Seq((a := AutoLoadScratchVar()).store(22), increment(a))
        compile_and_run(program)


def test_ALSV_from_scratch_var():
    @Subroutine(TealType.none)
    def increment(s: ScratchVar, a: Expr, s2: ScratchVar) -> Expr:
        alsv = AutoLoadScratchVar.from_scratch_var(s2)
        return Seq(
            alsv.increment(a),
            s.store(s.load() + a),
        )

    s1 = ScratchVar()
    s2 = ScratchVar()
    a = AutoLoadScratchVar()
    program = Seq(s2.store(Int(7312)), a.store(1111), s1.store(Int(2222)), increment(s1, a, s2), s1.load() * s2.load())
    stack, _ = compile_and_run(program)
    assert stack[0] == (2222 + 1111) * (7312 + 1111)
