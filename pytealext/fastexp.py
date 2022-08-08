from pyteal import BytesMul, Expr, If, Int, Itob, Return, ScratchVar, Seq, Subroutine, TealType, While

from pytealext import Mul128


@Subroutine(TealType.bytes, "pytealextFastExp")
def FastExp(base: Expr, exponent: Expr) -> Expr:
    """FastExp returns an expression which evaluates to base ** exponent, where base and exponent are uint64.

    It is assumed that 0 ** 0 = 1.
    The result of this operation is bytes.
    """
    current_exponent = ScratchVar(TealType.uint64)
    y = ScratchVar(TealType.bytes)
    x = ScratchVar(TealType.bytes)
    return Seq(
        If(exponent).Then(
            Seq(
                If(exponent == Int(1)).Then(Return(Itob(base))),
                x.store(Mul128(base, base)),
                If(exponent % Int(2))
                .Then(
                    #
                    y.store(Itob(base))
                )
                .Else(
                    #
                    y.store(Itob(Int(1)))
                ),
                current_exponent.store(exponent / Int(2)),
                While(current_exponent.load() > Int(1)).Do(
                    Seq(
                        If(current_exponent.load() % Int(2)).Then(y.store(BytesMul(x.load(), y.load()))),
                        x.store(BytesMul(x.load(), x.load())),
                        current_exponent.store(current_exponent.load() / Int(2)),
                    )
                ),
                Return(BytesMul(x.load(), y.load())),
            )
        ),
        # exponent == 0
        Return(Itob(Int(1))),
    )
