from inspect import getfullargspec

import pytest
from pyteal import Addr, App, Bytes, CompileOptions, Global, Int, Mode, TealBlock, TealComponent, TxnField, TxnType

from pytealext.inner_transactions import *  # pylint: disable=unused-wildcard-import

# According to PEP 468 order in kwargs is preserved, so we can safely check equality of Seqs


def get_arg_names(f):
    fas = getfullargspec(f)
    return fas.args  # list of parameter names

def get_arg_annotations(f) -> dict[str, str]:
    fas = getfullargspec(f)
    return fas.annotations  # dict of parameter names to annotations


compiler_v6 = CompileOptions(mode=Mode.Application, version=6)


def assert_equal_expr(ast_actual: Expr, ast_expected: Expr):
    actual, _ = ast_actual.__teal__(compiler_v6)
    actual.addIncoming()
    actual = TealBlock.NormalizeBlocks(actual)

    expected, _ = ast_expected.__teal__(compiler_v6)
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


@pytest.mark.parametrize(
    "inner_txn_function,type_enum",
    (
        (InnerPaymentTxn, TxnType.Payment),
        (InnerAssetTransferTxn, TxnType.AssetTransfer),
        (InnerAssetFreezeTxn, TxnType.AssetFreeze),
        (InnerAssetConfigTxn, TxnType.AssetConfig),
        (InnerApplicationCallTxn, TxnType.ApplicationCall),
    ),
)
def test_InnerTxns(inner_txn_function, type_enum):
    argspec = getfullargspec(inner_txn_function)

    for param in argspec.args: # for each function argument
        if "list" in str(argspec.annotations[param]): # if it's a list
            ast_actual = inner_txn_function(**{param: [App.localGet(Int(0), Bytes("test"))]})

            ast_expected = Seq(
                InnerTxnBuilder.SetField(TxnField.type_enum, type_enum),
                InnerTxnBuilder.SetField(TxnField[param], [App.localGet(Int(0), Bytes("test"))]),
            )
        else:
            ast_actual = inner_txn_function(**{param: App.localGet(Int(0), Bytes("test"))})

            ast_expected = Seq(
                InnerTxnBuilder.SetField(TxnField.type_enum, type_enum),
                InnerTxnBuilder.SetField(TxnField[param], App.localGet(Int(0), Bytes("test"))),
            )

        assert_equal_expr(ast_actual, ast_expected)


@pytest.mark.parametrize(
    "make_inner_expr,inner_expr",
    (
        (MakeInnerTxn, InnerTxn),
        (MakeInnerPaymentTxn, InnerPaymentTxn),
        (MakeInnerAssetTransferTxn, InnerAssetTransferTxn),
        (MakeInnerAssetFreezeTxn, InnerAssetFreezeTxn),
        (MakeInnerAssetConfigTxn, InnerAssetConfigTxn),
        (MakeInnerApplicationCallTxn, InnerApplicationCallTxn),
        (MakeInnerNoOpTxn, InnerNoOpTxn),
    ),
)
def test_MakeInnerGroupTxn_equivalence(make_inner_expr, inner_expr):
    """Test equivalence of single element GTxn with MakeInnerTxn"""

    assert_equal_expr(
        make_inner_expr(sender=Global.current_application_address(), fee=Int(997)),
        MakeInnerGroupTxn(inner_expr(sender=Global.current_application_address(), fee=Int(997))),
    )


def test_makeInnerGroupTxn():
    ast_actual = MakeInnerGroupTxn(
        InnerAssetFreezeTxn(freeze_asset_frozen=Int(0)),
        InnerAssetTransferTxn(asset_receiver=Addr("A7NMWS3NT3IUDMLVO26ULGXGIIOUQ3ND2TXSER6EBGRZNOBOUIQXHIBGDE")),
        InnerNoOpTxn(application_args=[Bytes("CALL"), Bytes("ME"), Bytes("MAYBE")]),
        InnerAssetConfigTxn(config_asset_unit_name=Bytes("AAA")),
    )

    ast_expected = Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.AssetFreeze),
        InnerTxnBuilder.SetField(TxnField.freeze_asset_frozen, Int(0)),
        InnerTxnBuilder.Next(),
        InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.AssetTransfer),
        InnerTxnBuilder.SetField(
            TxnField.asset_receiver, Addr("A7NMWS3NT3IUDMLVO26ULGXGIIOUQ3ND2TXSER6EBGRZNOBOUIQXHIBGDE")
        ),
        InnerTxnBuilder.Next(),
        InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.ApplicationCall),
        InnerTxnBuilder.SetField(TxnField.on_completion, OnComplete.NoOp),
        InnerTxnBuilder.SetField(TxnField.application_args, [Bytes("CALL"), Bytes("ME"), Bytes("MAYBE")]),
        InnerTxnBuilder.Next(),
        InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.AssetConfig),
        InnerTxnBuilder.SetField(TxnField.config_asset_unit_name, Bytes("AAA")),
        InnerTxnBuilder.Submit(),
    )

    assert_equal_expr(ast_actual, ast_expected)


def test_example_gtxn_compiles():
    """Test that example gtxn from docs compiles"""

    from pyteal import AppParam, MethodSignature, compileTeal, Approve
    from pytealext import MakeInnerGroupTxn, InnerNoOpTxn, InnerAssetTransferTxn

    app_to_call = Int(12345)
    amount_to_deposit = Int(100)
    asset_id = Int(222)
    app_address = AppParam.address(app_to_call)
    method = MethodSignature("deposit(string,axfer)void")

    # In the parent transaction the following must be set:
    # - Txn.accounts must contain the app_address
    # - Txn.assets must contain the asset_id
    # - Txn.applications must contain the app_id of the app called in the inner txn
    # otherwise the inner txn will fail
    # Should the fee be set to 0 like below, the parent transaction group should pay the fees
    deposit_and_call = Seq(
        app_address,
        MakeInnerGroupTxn(
            InnerAssetTransferTxn(
                asset_receiver=app_address.value(),
                asset_amount=amount_to_deposit,
                xfer_asset=asset_id,
                fee=Int(0), # must be pooled
            ),
            InnerNoOpTxn(
                application_id=app_to_call,
                application_args=[method, Bytes("Hello")],
                fee=Int(0), # must be pooled
            )
        ),
        Approve()
    )

    compileTeal(deposit_and_call, Mode.Application, version=6)
