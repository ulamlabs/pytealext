from typing import Iterator

from pyteal import (
    CompileOptions,
    Expr,
    Op,
    TealBlock,
    TealSimpleBlock,
    TealOp,
)

from pyteal.types import TealType, require_type

from .assemble import assemble_steps


class Mul128(Expr):
    """
    Mul128 calculates the expression m1 * m2, where m1 and m2 are TealType.uint64.
    The result of this operation is a bytes.
    """

    def __init__(self, m1: Expr, m2: Expr):
        """
        Args:
            ceiling: Calculate the m1 * m2
        """
        super().__init__()
        # make sure that argument expressions have the correct return type
        require_type(m1, TealType.uint64)
        require_type(m2, TealType.uint64)
        self.m1 = m1
        self.m2 = m2

    def _get_steps(self) -> Iterator[Expr or TealOp]:
        yield self.m1
        yield self.m2
        # mult args and return results as two uint64
        yield TealOp(self, Op.mulw)
        # int to bytes
        yield TealOp(self, Op.itob)
        # second int to bytes
        yield TealOp(self, Op.swap)
        yield TealOp(self, Op.itob)
        # return to right order
        yield TealOp(self, Op.swap)
        # concat two args -> uint128 (bytes)
        yield TealOp(self, Op.concat)

    def __teal__(self, options: CompileOptions) -> tuple[TealBlock, TealSimpleBlock]:
        return assemble_steps(self._get_steps(), options)

    def __str__(self):
        return f"(Mul128 {self.m1} {self.m2})"

    def type_of(self):
        return TealType.bytes

    def has_return(self):
        return False
