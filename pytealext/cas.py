from typing import Iterator

from pyteal import Expr, Op, TealBlock, TealSimpleBlock
from pyteal.types import require_type, TealType

from .assemble import assemble_steps


class CompareAndSelect(Expr):
    """
    Compare two values with a specified operator and condtitionally select one of them.
    if `lhs |op| rhs` succeds, rhs is returned.
    The lhs and rhs expressions are only evaluated once.
    """

    def __init__(self, lhs: Expr, rhs: Expr, op: Op, expected_type: TealType):
        super().__init__()
        self.lhs = lhs
        self.rhs = rhs
        self.op = op

        require_type(lhs.type_of(), expected_type)
        require_type(rhs.type_of(), expected_type)

    def type_of(self) -> TealType:
        return self.lhs.type_of()

    def has_return(self):
        return False

    def __str__(self):
        type_name = type(self).__name__
        # If instanced directly and not through subclass, display more helpful message
        if type_name == "CompareAndSelect":
            type_name = f"CompareAndSelect({str(self.op)})"
        return f"({type_name} {str(self.lhs)} {str(self.rhs)})"

    def _get_steps(self) -> Iterator[tuple]:
        """
        Steps of the program described in TEAL
        """
        yield (self.lhs,)
        yield (self.rhs,)
        yield (Op.dup2,)
        yield (self.op,)
        yield (Op.select,)

    def __teal__(self, options: "CompileOptions") -> tuple[TealBlock, TealSimpleBlock]:
        return assemble_steps(self._get_steps(), options, expr=self)


class Min(CompareAndSelect):
    """
    Expression calculating the minimum of two values.
    """

    def __init__(self, lhs: Expr, rhs: Expr):
        # lhs > rhs => value of rhs is returned
        super().__init__(lhs, rhs, Op.gt, TealType.uint64)


class Max(CompareAndSelect):
    """
    Expression calculating the maximum of two values.
    """

    def __init__(self, lhs: Expr, rhs: Expr):
        # lhs < rhs => value of rhs is returned
        super().__init__(lhs, rhs, Op.lt, TealType.uint64)
