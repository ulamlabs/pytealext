from pytealext import Uint64Array
from pyteal import Subroutine, Expr, TealType, For

@Subroutine(TealType.bytes)
def increment_each_element(encoded_arr: Expr, value: Expr) -> Expr:
    pass # TODO