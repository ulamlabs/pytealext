from typing import Iterator

from pyteal import CompileOptions, Expr, Int, Op, TealBlock, TealSimpleBlock
from pyteal.ir.tealop import TealOp
from pyteal.types import TealType, require_type

from .assemble import assemble_steps


class MulDiv64(Expr):
    """
    MulDiv64 calculates the expression m1 * m2 / d rounded down unless explicitly asked for the ceiling.
    The result of this operation is a 64 bit integer (the lower 64 bits of the 128 bit result).
    The bounds of the result are checked, and should it exceed the 64 bit integer capacity,
    the runtime will fail.
    """

    def __init__(self, m1: Expr, m2: Expr, d: Expr, ceiling: bool = False):
        """
        Args:
            ceiling: Calculate the ceiling of (m1*m2)/d instead of the floor
        """
        super().__init__()
        # make sure that argument expressions have the correct return type
        require_type(m1, TealType.uint64)
        require_type(m2, TealType.uint64)
        require_type(d, TealType.uint64)
        self.m1 = m1
        self.m2 = m2
        self.d = d
        self.ceiling = ceiling

    def _get_steps(self) -> Iterator[Expr or TealOp]:
        yield self.m1
        yield self.m2
        yield TealOp(self, Op.mulw)
        yield Int(0)  # higher 64 bits of the divisor
        yield self.d  # lower 64 bits of the divisor
        yield TealOp(self, Op.divmodw)
        # stack is: ..., div_hi, div_lo, mod_hi, mod_lo
        if self.ceiling:
            # should the result of the operation have a remainder, we add 1 to the result
            # we do this by calculating the logical or of the remainder which produces a result in range [0,1]
            yield TealOp(self, Op.logic_or)
            # the stack is: ..., div_hi, div_lo, (mod_hi || mod_lo)
            # if the addition overflows, the runtime will panic
            yield TealOp(self, Op.add)
            # the stack is: ..., div_hi, (div_lo + round_up_bit)
        else:
            # pop 128b remainder
            yield TealOp(self, Op.pop)
            yield TealOp(self, Op.pop)
        # put the higher 64 bits of the result on top of the stack
        yield TealOp(self, Op.swap)
        # check if the result overflew the 64 bit integer capacity
        yield TealOp(self, Op.logic_not)
        yield TealOp(self, Op.assert_)

    def __teal__(self, options: CompileOptions) -> tuple[TealBlock, TealSimpleBlock]:
        return assemble_steps(self._get_steps(), options)

    def __str__(self):
        return "(MulDiv64 {} {} {})".format(self.m1, self.m2, self.d)

    def type_of(self):
        return TealType.uint64

    def has_return(self):
        return False
