from typing import Optional

from pyteal import Expr, InnerTxnBuilder, Seq, TxnType, TxnField


def MakeInnerTxn(**kwargs: Optional[Expr]) -> Expr:
    """
    Create and execute arbitrary inner transaction.
    Universal txn maker, allows for setting any fields available in TxnField by name.
    This is a convenience function made for for other Make(.*) functions, and is not intended to be used directly.

    Args:
        kwargs: TxnField names mapped to Exprs, should any be set to None, they will be exluded from setFields

    Example:
    ```
    MakeInnerTxn(
        receiver=Addr(addr_a)
        fee=Int(0),
        sender=None,
    )
    is equivalent (in terms of functionality) to:
    Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetField(TxnField.receiver, Addr(addr_a)),
        InnerTxnBuilder.SetField(TxnField.fee, Int(0)),
        InnerTxnBuilder.Submit()
    )
    ```

    Note:
        Some of the fields may not be available to be set by the inner transaction
        (ex. rekey_to, accounts (as of TEAL5))
        List of fields that can be set:
        https://developer.algorand.org/docs/get-details/dapps/smart-contracts/apps/#setting-transaction-properties
    """
    fields_to_exprs = {TxnField[name]: expr for name, expr in kwargs.items() if expr is not None}
    return Seq(
        # black: dont-compact-seq
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(fields_to_exprs),
        InnerTxnBuilder.Submit()
    )


# pylint: disable=unused-argument


def MakeInnerPaymentTxn(
    sender: Optional[Expr] = None,
    receiver: Optional[Expr] = None,
    amount: Optional[Expr] = None,
    close_remainder_to: Optional[Expr] = None,
    fee: Optional[Expr] = None,
) -> Expr:
    """
    Create and execute an inner payment txn.

    Args:
        sender: The sender address in the transaction,
            only makes sense to set this field if sending from an address rekeyed to smart contract controlled address.
            The default is smart contract controlled address.
        receiver: Address of the receiver of the Algo transfer
        amount: Amount of microAlgos to transfer
        close_remainder_to: Close Algo balance to this address
        fee: The fee for the transaction in microAlgos

    If any of those parameters is set to None, then a default is used.
    The defaults are explained here:
    https://pyteal.readthedocs.io/en/latest/api.html#pyteal.InnerTxnBuilder
    """
    return MakeInnerTxn(type_enum=TxnType.Payment, **locals())


def MakeInnerAssetTransferTxn(
    sender: Optional[Expr] = None,
    asset_receiver: Optional[Expr] = None,
    asset_amount: Optional[Expr] = None,
    xfer_asset: Optional[Expr] = None,
    asset_close_to: Optional[Expr] = None,
    fee: Optional[Expr] = None,
) -> Expr:
    """
    Create and execute an inner asset transfer.

    Args:
        sender: The sender address in the transaction,
            only makes sense to set this field if sending from an address rekeyed to smart contract controlled address.
            The default is smart contract controlled address.
        asset_receiver: Receiver of the asset transfer
        asset_amount: Amount of asset to transfer
        xfer_asset: Transferred asset ID
        asset_close_to: Close Algo balance to this address
        fee: The fee for the transaction in microAlgos

    If any of those parameters is set to None, then a default is used.
    The defaults are explained here:
    https://pyteal.readthedocs.io/en/latest/api.html#pyteal.InnerTxnBuilder
    """
    return MakeInnerTxn(type_enum=TxnType.AssetTransfer, **locals())


def MakeInnerAssetFreezeTxn(
    sender: Optional[Expr] = None,
    freeze_asset: Optional[Expr] = None,
    freeze_asset_account: Optional[Expr] = None,
    freeze_asset_frozen: Optional[Expr] = None,
    fee: Optional[Expr] = None,
) -> Expr:
    """
    Create and execute inner asset freeze transaction

    Args:
        sender: The sender address in the transaction, should be a freeze manager of the asset.
            The default is smart contract controlled address.
        freeze_asset: Asset ID which will be frozen
        freeze_asset_account: Account which will have their asset frozen
        freeze_asset_frozen: {0,1} set the new freeze state (0 not frozen, 1 frozen)
        fee: The fee for the transaction in microAlgos

    All freeze_* parameters should be set. Not setting them will cause Undocumented Behaviour.
    """
    return MakeInnerTxn(type_enum=TxnType.AssetFreeze, **locals())


def MakeInnerAssetConfigTxn(
    sender: Optional[Expr] = None,
    config_asset: Optional[Expr] = None,
    config_asset_total: Optional[Expr] = None,
    config_asset_default_frozen: Optional[Expr] = None,
    config_asset_unit_name: Optional[Expr] = None,
    config_asset_name: Optional[Expr] = None,
    config_asset_manager: Optional[Expr] = None,
    config_asset_reserve: Optional[Expr] = None,
    config_asset_freeze: Optional[Expr] = None,
    config_asset_clawback: Optional[Expr] = None,
    config_asset_url: Optional[Expr] = None,
    config_asset_metadata_hash: Optional[Expr] = None,
    config_asset_decimals: Optional[Expr] = None,
    fee: Optional[Expr] = None,
) -> Expr:
    """
    Create and execute inner asset configure transaction

    Args:
        sender: The sender's address. Leave it empty and it will be autoset to contract's address.
        config_asset: Asset ID to be configured (leave empty when creating new ASA)
        config_asset_total: Total created tokens of the new ASA
        config_asset_default_frozen: Whether slots for this asset in user
            accounts are frozen by default
        config_asset_unit_name: name of a unit of this asset
        config_asset_name: name of the asset
        config_asset_manager: address allowed to change nonzero addresses
            for this asset
        config_asset_reserve: account whose holdings of this asset should
            be reported as "not minted"
        config_asset_freeze: account allowed to change frozen state of
            holdings of this asset
        config_asset_clawback: account allowed take units of this asset
            from any account
        config_asset_url: a URL where more information about the asset
            can be retrieved
        config_asset_metadata_hash: a commitment to some unspecified
            asset metadata (32 byte hash)
        config_asset_decimals: a commitment to some unspecified
            asset metadata (32 byte hash)
        fee: The fee for the transaction in microAlgos

    Some of the descriptions come from py-algorand-sdk.

    For more details about parameters needed for your use-case visit:
    https://developer.algorand.org/docs/get-details/transactions/transactions/#asset-configuration-transaction

    NOTE:
        When changing one address (manager, reserve, freeze, clawback),
        all others must be set again or they will be cleared.
        Cleared addresses will be locked forever.
    """
    return MakeInnerTxn(type_enum=TxnType.AssetConfig, **locals())
