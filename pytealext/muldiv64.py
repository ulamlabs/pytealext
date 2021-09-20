from typing import Iterator

from pyteal import Expr, Int, Op, TealBlock, TealSimpleBlock
from pyteal.types import require_type, TealType

from .assemble import assemble_steps


class MulDiv64(Expr):
    """
    MulDiv64 calculates the expression m1 * m2 / d (rounded down).
    The result of this operation is a 64 bit integer (the lower 64 bits of the 128 bit result).
    By default, the bounds of the result are checked, and should it exceed the 64 bit integer capacity, 
    the runtime will fail.
    """

    def __init__(self, m1: Expr, m2: Expr, d: Expr, check_bounds: bool = True):
        """
        Args:
            check_bounds: make an assertion that the result fits in a 64-bit integer
                if set to False, lower 64 bits of the result are returned
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

    def _get_steps(self) -> Iterator[tuple]:
        yield (Op.mulw, self.m1, self.m2)
        yield (Int(0),)
        yield (self.d,)
        yield (Op.divmodw,)
        # pop 128b remainder
        yield (Op.pop,)
        yield (Op.pop,)
        # store the lower 64 bits
        yield (Op.swap,)
        if self.check_bounds:
            yield (Op.logic_not,)
            yield (Op.assert_,)
        else:
            yield (Op.pop,)

    def __teal__(self, options: "CompileOptions") -> tuple[TealBlock, TealSimpleBlock]:
        return assemble_steps(self._get_steps(), options, expr=self)

    def __str__(self):
        return "(MulDiv64 {} {} {})".format(self.m1, self.m2, self.d)

    def type_of(self):
        return TealType.uint64

    def has_return(self):
        return False
