from typing import Iterator

from pyteal import Expr, Int, Op, TealBlock, TealSimpleBlock
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

    def __teal__(self, options: "CompileOptions") -> tuple[TealBlock, TealSimpleBlock]:
        return new_assembler(self._get_steps(), options)
        # compile multiplication arguments
        # m1_start, m1_end = self.m1.__teal__(options)
        # m2_start, m2_end = self.m2.__teal__(options)
        # m1_end.setNextBlock(m2_start)
        # # calculate mulw(m1,m2)
        # multiply = TealSimpleBlock([TealOp(self, Op.mulw)])
        # m2_end.setNextBlock(multiply)
        # end = multiply
        # if self.ceiling:
        #     # perform the ceiling operation by property: ⌈x/y⌉ = ⌊(x+y-1)/y⌋
        #     # in this case it transaltes to: ⌈(m1*m2)/d⌉ = ⌊(m1*m2+d-1)/d⌋
        #     # the stack is: ..., mul_hi, mul_lo
        #     # below we emulate 128 bit addition of the result of multiplication and d-1
        #     d_start, d_end = self.d.__teal__(options)
        #     end.setNextBlock(d_start)
        #     ceiling = TealSimpleBlock(
        #         [
        #             # load int 1
        #             TealOp(self, Op.int, 1),
        #             # subtract 1 from d
        #             TealOp(self, Op.minus),
        #             # add d to the result of the multiplication (lower 64 bits)
        #             TealOp(self, Op.addw),
        #             # The stack is: ..., mul_hi, add_hi, add_lo
        #             # hide the lower 64 bits of the addition result
        #             TealOp(self, Op.cover, 2),
        #             # The stack is: ..., add_lo, mul_hi, add_hi
        #             # add the high results and swap to return the high bits where they belong
        #             TealOp(self, Op.add),
        #             TealOp(self, Op.swap),
        #         ]
        #     )
        #     d_end.setNextBlock(ceiling)
        #     end = ceiling
        # int_0 = TealSimpleBlock([TealOp(self, Op.int, 0)])
        # end.setNextBlock(int_0)
        # d_start, d_end = self.d.__teal__(options)
        # int_0.setNextBlock(d_start)
        # # calculate divmodw(mul_hi, mul_lo, Int(0), d)
        # divmodw = TealSimpleBlock([
        #     TealOp(self, Op.divmodw),
        #     # pop 128b remainder
        #     TealOp(self, Op.pop),
        #     TealOp(self, Op.pop),
        #     # store the lower 64 bits
        #     TealOp(self, Op.swap),
        # ])
        # d_end.setNextBlock(divmodw)
        # end = divmodw
        # if self.check_bounds:
        #     # check that the result fits in a 64-bit integer
        #     # if not, fail
        #     check_bounds = TealSimpleBlock([
        #         TealOp(self, Op.logic_not),
        #         TealOp(self, Op.assert_),
        #     ])
        #     end.setNextBlock(check_bounds)
        #     end = check_bounds
        # else:
        #     # pop the upper 64 bits
        #     pop = TealSimpleBlock([TealOp(self, Op.pop)])
        #     end.setNextBlock(pop)
        #     end = pop
        # return m1_start, end

    def __str__(self):
        return "(MulDiv64 {} {} {})".format(self.m1, self.m2, self.d)

    def type_of(self):
        return TealType.uint64

    def has_return(self):
        return False
