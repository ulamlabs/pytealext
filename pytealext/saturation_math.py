from pyteal import Expr, If, Int

MAX_UINT64 = 2**64 - 1
MAX_UINT64_EXPR = Int(MAX_UINT64)


def SaturatingAdd(a: Expr, b: Expr) -> Expr:
    """
    Returns a + b, saturating at MAX_UINT64.
    """
    return If(a > MAX_UINT64_EXPR - b, MAX_UINT64_EXPR, a + b)


def SaturatingSub(a: Expr, b: Expr) -> Expr:
    """
    Returns a - b, saturating at 0.
    """
    return If(a < b, Int(0), a - b)
