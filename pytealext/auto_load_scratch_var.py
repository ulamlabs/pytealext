from pyteal import Bytes, CompileOptions, Expr, Int, ScratchVar, TealBlock, TealSimpleBlock, TealType


class AutoLoadScratchVar(Expr):
    """Makes ScratchVars more convenient to use.

    When used inline with another expression, a load is performed automatically
    without the need for explicit load() calls.

    Store still has to be called manually.

    Example:
    ```
        s = AutoLoadScratchVar(TealType.uint64)
        sum = AutoLoadScratchVar(TealType.uint64)
        program = For(s.store(Int(0)), s < Int(10), s.increment()).Do(
            sum.increment(s)
        )
    ```
    """

    def __init__(
        self, type: TealType = TealType.anytype, slotId: int | None = None
    ):  # pylint: disable=redefined-builtin
        self.scratch_var = ScratchVar(type, slotId)
        Expr.__init__(self)

    @classmethod
    def from_scratch_var(cls, scratch_var: ScratchVar) -> "AutoLoadScratchVar":
        """Upgrade a ScratchVar to an AutoLoadScratchVar"""
        c = cls()
        c.scratch_var = scratch_var
        return c

    def index(self) -> Expr:
        """Get the index of the used scratch slot"""
        return self.scratch_var.index()

    def load(self) -> Expr:
        """Load the value from the scratch space"""
        return self.scratch_var.load()

    def storage_type(self) -> TealType:
        """Get the type of expressions that can be stored in this ScratchVar."""
        return self.scratch_var.storage_type()

    def store(self, value: Expr | int | str | bytes) -> Expr:
        """Store the given value in the scratch space"""
        match value:
            case int(v):
                value = Int(v)
            case str(v) | bytes(v):
                value = Bytes(v)  # type: ignore
            case Expr():
                pass
            case _:
                raise TypeError(f"Invalid type for ScratchVarPro.store: {type(value)}")
        # superclass's store will check for correct stack type
        return self.scratch_var.store(value)  # type: ignore

    def increment(self, value: Expr | int = 1) -> Expr:
        """Increase the value in the scratch space by the given value (1 by default)"""
        if isinstance(value, int):
            value = Int(value)
        return self.store(self.load() + value)

    def decrement(self, value: Expr | int = 1) -> Expr:
        """Decrease the value in the scratch space by the given value (1 by default)"""
        if isinstance(value, int):
            value = Int(value)
        return self.store(self.load() - value)

    def type_of(self) -> TealType:
        return self.scratch_var.type

    def has_return(self) -> bool:
        return False

    def __str__(self) -> str:
        return self.load().__str__()

    def __teal__(self, options: CompileOptions) -> tuple[TealBlock, TealSimpleBlock]:
        return self.load().__teal__(options)
