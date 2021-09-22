from pyteal import Expr, If, Int, Not, TealBlock, TealSimpleBlock, TealInputError
from pyteal.types import require_type, TealType


class LazyAnd(Expr):
    """
    Lazily evaluate And applied to args.
    Evaluate And(...) and cease operation on the first expr that evaluates to false.
    """

    def __init__(self, *args: Expr):
        super().__init__()
        self.args = args
        for arg in args:
            require_type(arg.type_of(), TealType.uint64)
        if len(args) < 1:
            raise TealInputError("LazyAnd expects at least 1 argument")

    def type_of(self) -> TealType:
        return TealType.uint64

    def has_return(self):
        return False

    def __str__(self):
        return "(LazyAnd " + " ".join(map(str, self.args)) + ")"

    def _build_ast(self, remaining: list[Expr]):
        if len(remaining) == 0:
            raise ValueError("list of remaining expressions unexpectedly shrunk to 0")
        if len(remaining) == 1:
            return remaining[0]
        return If(remaining[0]).Then(self._build_ast(remaining[1:])).Else(Int(0))

    def __teal__(self, options: "CompileOptions") -> tuple[TealBlock, TealSimpleBlock]:
        return self._build_ast(self.args).__teal__(options)


class LazyOr(Expr):
    """
    Lazily Evaluated Or
    Ceases operation on the first argument that evaluates to true.
    """

    def __init__(self, *args: Expr):
        super().__init__()
        self.args = args
        for arg in args:
            require_type(arg.type_of(), TealType.uint64)
        if len(args) < 1:
            raise TealInputError("LazyOr expects at least 1 argument")

    def type_of(self) -> TealType:
        return TealType.uint64

    def has_return(self):
        return False

    def __str__(self):
        return "(LazyOr " + " ".join(map(str, self.args)) + ")"

    def _assemble(self, remaining: list[Expr]):
        if len(remaining) == 0:
            raise ValueError("list of remaining expressions unexpectedly shrunk to 0")
        if len(remaining) == 1:
            return remaining[0]
        return If(remaining[0]).Then(Int(1)).Else(self._assemble(remaining[1:]))

    def __teal__(self, options: "CompileOptions") -> tuple[TealBlock, TealSimpleBlock]:
        return self._assemble(self.args).__teal__(options)
