from pyteal import (
    Bytes,
    BytesMul,
    Concat,
    Expr,
    ExtractUint64,
    For,
    If,
    Int,
    Itob,
    Len,
    Replace,
    Return,
    ScratchVar,
    Seq,
    Subroutine,
    TealType,
)

from pytealext import Mul128


class Uint64Array:
    """Abstraction layer for handling arrays of uint64s stored as bytes

    The array must be initialized either by calling initialize() or decode().

    The binary representation of the array is densely packed uints64.

    Example usage:
    ```
        arr = Uint64Array()
        program = Seq(
            arr.decode(BytesZero(Int(16))),
            Assert(arr[0] == arr[1])
        )
    ```
    Example append:
    ```
        arr = Uint64Array()
        program = Seq(
            arr.initialize(),
            arr.append(Int(1)),
            arr.append(Int(2)),
            arr.append(Int(3)),
            Assert(arr[1] == Int(2))
        )
    ```

    Note:
        `.set()` method requires TEALv7+
    """

    def __init__(self) -> None:
        self.cache = ScratchVar(TealType.bytes)

    def initialize(self) -> Expr:
        """Initialize an empty array.

        If the array is already initialized, this will clear it.
        """
        return self.cache.store(Bytes(""))

    def decode(self, value: Expr) -> Expr:
        """Decode a bytestring into an array of uint64s.

        This method initializes the array.
        If the array is already initialized, previous content will be lost.

        Lazy, complexity: O(1)
        """
        return self.cache.store(value)

    def encode(self) -> Expr:
        """Retrieve the binary string representation of this array."""
        return self.cache.load()

    def append(self, value: Expr) -> Expr:
        """Append a new element to the end of this array."""
        return self.cache.store(Concat(self.cache.load(), Itob(value)))

    def set(self, index: Expr | int, value: Expr) -> Expr:
        """Set the value at the given index to the given value."""
        if isinstance(index, int):
            position = Int(index * 8)
        else:
            position = index * Int(8)
        return self.cache.store(Replace(self.cache.load(), position, Itob(value)))

    def len(self) -> Expr:
        """Retrieve the expression evaluating to the length of this array."""
        return Len(self.encode()) / Int(8)

    def __getitem__(self, index: Expr | int) -> Expr:
        """Retrieve the value at the given index."""
        if isinstance(index, int):
            position = Int(index * 8)
        else:
            position = index * Int(8)
        return ExtractUint64(self.cache.load(), position)

    def sum(self):
        """Calculate the sum of the values.

        If the sum is greater or equal to 2^64, the runtime will panic.
        """
        return _array_sum(self.cache.load())

    def product_bytes(self):
        """Calculate the product of the values.

        The result is a standard TEAL big int.

        NOTE: Product of a 0 length array is one.
        """
        return _array_product_bytes(self.cache.load())

    def exists(self, value: Expr):
        """Check if a value exists in the array."""
        return _exists(self.cache.load(), value)


@Subroutine(TealType.uint64)
def _exists(cache: Expr, value: Expr) -> Expr:
    i = ScratchVar(TealType.uint64)
    inner_array = Uint64Array()

    return Seq(
        inner_array.decode(cache),
        For(i.store(Int(0)), i.load() < inner_array.len(), i.store(i.load() + Int(1))).Do(
            If(inner_array[i.load()] == value).Then(Return(Int(1)))
        ),
        Return(Int(0)),
    )


@Subroutine(TealType.uint64)
def _array_sum(cache: Expr) -> Expr:
    inner_array = Uint64Array()
    S = ScratchVar(TealType.uint64)
    i = ScratchVar(TealType.uint64)
    n = ScratchVar(TealType.uint64)

    return Seq(
        inner_array.decode(cache),
        n.store(inner_array.len()),
        S.store(Int(0)),
        For(i.store(Int(0)), i.load() < n.load(), i.store(i.load() + Int(1))).Do(
            S.store(S.load() + inner_array[i.load()])
        ),
        S.load(),
    )


@Subroutine(TealType.bytes)
def _array_product_bytes(cache: Expr) -> Expr:
    inner_array = Uint64Array()
    P = ScratchVar(TealType.bytes)
    i = ScratchVar(TealType.uint64)
    n = ScratchVar(TealType.uint64)
    return Seq(
        inner_array.decode(cache),
        n.store(inner_array.len()),
        If(n.load())
        .Then(
            If(n.load() == Int(1))
            .Then(
                Itob(inner_array[0]),
            )
            .Else(
                Seq(
                    P.store(Mul128(inner_array[0], inner_array[1])),
                    # In this algorithm next values are multiplied in pair and
                    # next multiplied by counter because Mul128 is cheaper then BytesMul
                    For(i.store(Int(3)), i.load() < n.load(), i.store(i.load() + Int(2))).Do(
                        P.store(BytesMul(P.load(), Mul128(inner_array[i.load() - Int(1)], inner_array[i.load()])))
                    ),
                    If(n.load() % Int(2) == Int(1)).Then(
                        # black: no line break
                        P.store(BytesMul(P.load(), Itob(inner_array[n.load() - Int(1)])))
                    ),
                    P.load(),
                )
            ),
        )
        .Else(Itob(Int(1))),
    )
