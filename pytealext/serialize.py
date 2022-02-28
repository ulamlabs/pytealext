from pyteal import (
    CompileOptions,
    Concat,
    Expr,
    ExtractUint16,
    ExtractUint32,
    ExtractUint64,
    Int,
    Itob,
    Op,
    ScratchSlot,
    ScratchVar,
    Seq,
    TealBlock,
    TealOp,
    TealType,
)
from pyteal.errors import verifyTealVersion
from pyteal.types import require_type


class ExtractSL(Expr):
    """
    Extract a slice from a bytes value with fixed starting point and length.

    More efficient than Extract if start and length are known while building the AST.

    This will become obsolete in the upcoming PyTEAL version
    """

    def __init__(self, start: int, length: int, arg: Expr):
        super().__init__()
        require_type(arg, TealType.bytes)
        if start > 255 or start < 0:
            raise ValueError("start must be between 0 and 255")
        if length > 255 or length < 0:
            raise ValueError("length must be between 0 and 255")
        self.arg = arg
        self.start = start
        self.length = length

    def __teal__(self, options: CompileOptions):
        verifyTealVersion(
            Op.extract.min_version,
            options.version,
            f"TEAL version too low to use op {Op.extract}",
        )

        return TealBlock.FromOp(options, TealOp(self, Op.extract, self.start, self.length), self.arg)

    def __str__(self):
        return f"({Op.extract} {self.start} {self.length} {self.arg})"

    def type_of(self):
        return TealType.bytes

    def has_return(self):
        return False


def SerializeIntegers(*ints: Expr, width: int = 64) -> Expr:
    """
    Serialize a sequence of integers into a byte string.

    Each expression provided as an argument must evaluate to uint64.

    Should the width be less than 64, the integers' higher bits will be trimmed for performance reasons.

    Should be used together with deserialize to guarantee proper formatting.

    Args:
        ints: The integers to serialize.
        width (optional): The width of the integers to serialize in bits. Defaults to 64. Allowed values are 16, 32, 64.
    """
    if width == 64:
        return Concat(*[Itob(i) for i in ints])
    elif width == 32:
        # extract the lowest 32 bits (4 bytes) from each integer
        return Concat(*[ExtractSL(4, 4, Itob(i)) for i in ints])
    elif width == 16:
        # extract the lowest 16 bits (2 bytes) from each integer
        return Concat(*[ExtractSL(6, 2, Itob(i)) for i in ints])
    else:
        raise ValueError(f"Invalid width: {width}")


class DeserializeIntegers:
    """
    Deserialize bytes into a sequence of integers.
    The deserialized integers are put in the provided slots.
    This function will fail on runtime if the byte string is too short.

    NOTE: "serialized" is evaluated each time a value is accessed.
        Therefore it should not produce side-effects.
        For optimal performance serialized could be a slot.load() expression.

    Args:
        serialized: The byte string to deserialize.
        slots: The scratch slots to put the deserialized integers in.
    """

    def __init__(self, serialized: Expr, *, width: int = 64):
        self.serialized = serialized
        self.bytes_width = width // 8

        if width == 16:
            self.ExtractUint = ExtractUint16
        elif width == 32:
            self.ExtractUint = ExtractUint32
        elif width == 64:
            self.ExtractUint = ExtractUint64
        else:
            raise ValueError(f"Invalid width: {width}")

    def __getitem__(self, index: int or Expr) -> Expr:
        if isinstance(index, int):
            return self.ExtractUint(self.serialized, Int(index * self.bytes_width))

        require_type(index, TealType.uint64)
        return self.ExtractUint(self.serialized, index * Int(self.bytes_width))


def DeserializeIntegersToSlots(serialized: Expr, *slots: ScratchVar or ScratchSlot, width: int = 64) -> Expr:
    """
    Deserialize bytes into a sequence of integers.
    The deserialized integers are put in the provided slots.
    This function will fail on runtime if the byte string is too short.

    `serialized` will be stored in the scratch space for efficiency and therefore only evaluated once.

    Args:
        serialized: The byte string to deserialize.
        slots: The scratch slots to put the deserialized integers in.
    """
    if width == 16:
        ExtractUint = ExtractUint16
    elif width == 32:
        ExtractUint = ExtractUint32
    elif width == 64:
        ExtractUint = ExtractUint64
    else:
        raise ValueError(f"Invalid width: {width}")

    # guarantee fast access for extract uint
    tmp = ScratchVar()

    byte_width = width // 8
    return Seq(
        tmp.store(serialized),
        *[slot.store(ExtractUint(tmp.load(), Int(i * byte_width))) for i, slot in enumerate(slots)],
    )
