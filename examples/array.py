from pyteal import Assert, Expr, For, Int, ScratchVar, Seq, Subroutine, TealType

from pytealext import Uint64Array
from pytealext.array import INDEX_NOT_FOUND, array_exists, array_index


@Subroutine(TealType.bytes)
def increment_each_element(encoded_arr: Expr, value: Expr) -> Expr:
    """Create a copy of an arra"""
    array_in = Uint64Array()
    result = Uint64Array()
    n = ScratchVar(TealType.uint64)
    return Seq(
        array_in.decode(encoded_arr),
        n.store(array_in.length()),
        result.initialize(),
        For((i := ScratchVar()).store(Int(0)), i.load() < n.load(), i.store(i.load() + Int(1))).Do(
            result.append(array_in[i.load()] + value)
        ),
        result.encode(),
    )


def increment_program() -> Expr:
    """Example for running the above subroutine."""
    array_in = Uint64Array()
    array_out = Uint64Array()
    return Seq(
        array_in.initialize(),
        array_in.append(Int(1000)),
        array_in.append(Int(2)),
        array_in.append(Int(3)),
        array_in.append(Int(4)),
        array_out.decode(increment_each_element(array_in.encode(), Int(1000))),
        Assert(array_out[0] == Int(2000)),
        Assert(array_out[1] == Int(1002)),
        Assert(array_out[2] == Int(1003)),
        Assert(array_out[3] == Int(1004)),
        Int(1),
    )


def search_array() -> Expr:
    array = Uint64Array()
    return Seq(
        array.initialize(),
        array.append(Int(1000)),
        array.append(Int(2)),
        array.append(Int(3)),
        array.append(Int(4)),
        Assert(array.index(Int(1000)) == Int(0)),
        # find index without the abstraction (useful in subroutines)
        Assert(array_index(array.encode(), Int(3)) == Int(2)),
        Assert(array_index(array.encode(), Int(1)) == INDEX_NOT_FOUND),
        Assert(array.exists(Int(3)) == Int(1)),
        Assert(array_exists(array.encode(), Int(1)) == Int(0)),
        Int(1),
    )
