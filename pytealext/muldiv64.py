from typing import Iterator

from pyteal import CompileOptions, Expr, Int, Op, TealBlock, TealSimpleBlock
from pyteal.ir.tealop import TealOp
from pyteal.types import TealType, require_type

from .assemble import new_assembler


class MulDiv64(Expr):
    """
    MulDiv64 calculates the expression m1 * m2 / d rounded down unless explicitly asked for the ceiling.
    The result of this operation is a 64 bit integer (the lower 64 bits of the 128 bit result).
    By default, the bounds of the result are checked, and should it exceed the 64 bit integer capacity,
    the runtime will fail.
    """

    def __init__(self, m1: Expr, m2: Expr, d: Expr, check_bounds: bool = True, ceiling: bool = False):
        """
        Args:
            check_bounds: make an assertion that the result fits in a 64-bit integer
                if set to False, lower 64 bits of the result are returned
            ceiling: Calculate the ceiling of (m1*m2)/d instead of the floor
        """
        super().__init__()
        # make sure that argument expressions have the correct return type
        require_type(m1.type_of(), TealType.uint64)
        require_type(m2.type_of(), TealType.uint64)
        require_type(d.type_of(), TealType.uint64)
        self.m1 = m1
        self.m2 = m2
        self.d = d
        self.check_bounds = check_bounds
        self.ceiling = ceiling

    def _get_steps(self) -> Iterator[Expr or TealOp]:
        yield self.m1
        yield self.m2
        yield TealOp(self, Op.mulw)
        if self.ceiling:
            # perform the ceiling operation by property: ⌈x/y⌉ = ⌊(x+y-1)/y⌋
            # in this case it transaltes to: ⌈(m1*m2)/d⌉ = ⌊(m1*m2+d-1)/d⌋
            # the stack is: ..., mul_hi, mul_lo
            # below we emulate 128 bit addition of the result of multiplication and d-1
            yield self.d
            yield Int(1)
            yield TealOp(self, Op.minus)
            # the stack is: ..., mul_hi, mul_lo, (d-1)
            yield TealOp(self, Op.addw)
            # the stack is: ..., mul_hi, add_hi, add_lo
            # to get the expected result high bits need to be added
            yield TealOp(self, Op.cover, 2)
            # the stack is: ..., add_lo, mul_hi, add_hi
            # add the high results and swap to return the high bits where they belong
            yield TealOp(self, Op.add)
            yield TealOp(self, Op.swap)
        yield Int(0)  # higher 64 bits of the divisor
        yield self.d  # lower 64 bits of the divisor
        yield TealOp(self, Op.divmodw)
        # pop 128b remainder
        yield TealOp(self, Op.pop)
        yield TealOp(self, Op.pop)
        # store the lower 64 bits
        yield TealOp(self, Op.swap)
        if self.check_bounds:
            yield TealOp(self, Op.logic_not)
            yield TealOp(self, Op.assert_)
        else:
            yield TealOp(self, Op.pop)

    def __teal__(self, options: CompileOptions) -> tuple[TealBlock, TealSimpleBlock]:
        return new_assembler(self._get_steps(), options)

    def __str__(self):
        return "(MulDiv64 {} {} {})".format(self.m1, self.m2, self.d)

    def type_of(self):
        return TealType.uint64

    def has_return(self):
        return False
