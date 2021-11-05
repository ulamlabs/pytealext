from inspect import getfullargspec

import pytest
from pyteal import Addr, App, Bytes, CompileOptions, Global, Int, Mode, TealBlock, TealComponent, TxnField, TxnType

from pytealext.inner_transactions import *  # pylint: disable=unused-wildcard-import

# According to PEP 468 order in kwargs is preserved, so we can safely check equality of Seqs


def get_arg_names(f):
    fas = getfullargspec(f)
    return fas[0]  # list of parameter names


compiler_v5 = CompileOptions(mode=Mode.Application, version=5)


def assert_equal_expr(ast_actual: Expr, ast_expected: Expr):
    actual, _ = ast_actual.__teal__(compiler_v5)
    actual.addIncoming()
    actual = TealBlock.NormalizeBlocks(actual)

    expected, _ = ast_expected.__teal__(compiler_v5)
    expected.addIncoming()
    expected = TealBlock.NormalizeBlocks(expected)

    with TealComponent.Context.ignoreExprEquality():
        assert actual == expected


def test_MakeInnerTxn_fails_with_wrong_param():
    with pytest.raises(KeyError):
        _ = MakeInnerTxn(type=Bytes("pay"), cheeseburger=Int(3))


def test_MakeInnerPaymentTxn():
    ast_actual = MakeInnerPaymentTxn(
        sender=Global.current_application_address(),
        receiver=Addr("A7NMWS3NT3IUDMLVO26ULGXGIIOUQ3ND2TXSER6EBGRZNOBOUIQXHIBGDE"),
        amount=App.localGet(Int(0), Bytes("AAA")),
        close_remainder_to=Addr("7777777777777777777777777777777777777777777777777774MSJUVU"),
        fee=Int(10),
    )

    ast_expected = Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.Payment,
                TxnField.sender: Global.current_application_address(),
                TxnField.receiver: Addr("A7NMWS3NT3IUDMLVO26ULGXGIIOUQ3ND2TXSER6EBGRZNOBOUIQXHIBGDE"),
                TxnField.amount: App.localGet(Int(0), Bytes("AAA")),
                TxnField.close_remainder_to: Addr("7777777777777777777777777777777777777777777777777774MSJUVU"),
                TxnField.fee: Int(10),
            }
        ),
        InnerTxnBuilder.Submit(),
    )

    assert_equal_expr(ast_actual, ast_expected)


def test_MakeInnerAssetTransferTxn():
    params = get_arg_names(MakeInnerAssetTransferTxn)

    for param in params:
        ast_actual = MakeInnerAssetTransferTxn(**{param: App.localGet(Int(0), Bytes("test"))})

        ast_expected = Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.AssetTransfer),
            InnerTxnBuilder.SetField(TxnField[param], App.localGet(Int(0), Bytes("test"))),
            InnerTxnBuilder.Submit(),
        )

        assert_equal_expr(ast_actual, ast_expected)


def test_MakeInnerAssetFreezeTxn():
    params = get_arg_names(MakeInnerAssetFreezeTxn)

    for param in params:
        ast_actual = MakeInnerAssetFreezeTxn(**{param: App.localGet(Int(0), Bytes("test"))})

        ast_expected = Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.AssetFreeze),
            InnerTxnBuilder.SetField(TxnField[param], App.localGet(Int(0), Bytes("test"))),
            InnerTxnBuilder.Submit(),
        )

        assert_equal_expr(ast_actual, ast_expected)


def test_MakeInnerAssetConfigTxn():
    params = get_arg_names(MakeInnerAssetConfigTxn)

    for param in params:
        ast_actual = MakeInnerAssetConfigTxn(**{param: App.localGet(Int(0), Bytes("test"))})

        ast_expected = Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.AssetConfig),
            InnerTxnBuilder.SetField(TxnField[param], App.localGet(Int(0), Bytes("test"))),
            InnerTxnBuilder.Submit(),
        )

        assert_equal_expr(ast_actual, ast_expected)
