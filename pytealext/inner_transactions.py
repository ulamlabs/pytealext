from typing import Optional

from pyteal import CompileOptions, Expr, InnerTxnBuilder, OnComplete, Seq, TealBlock, TealSimpleBlock, TealType, TxnField, TxnType


class InnerTxn(Expr):
    """
    An Expression setting fields for a transaction.
    It is equivalent to the InnerTxnBuilder.SetFields(...) expression.
    """

    def __init__(self, **kwargs: Optional[Expr]):
        super().__init__()
        fields_to_exprs = {TxnField[name]: expr for name, expr in kwargs.items() if expr is not None}

        self.expr = InnerTxnBuilder.SetFields(fields_to_exprs)

    def type_of(self) -> TealType:
        return TealType.none

    def has_return(self) -> bool:
        return False

    def __str__(self) -> str:
        return str(self.expr)

    def __teal__(self, options: CompileOptions) -> tuple[TealBlock, TealSimpleBlock]:
        return self.expr.__teal__(options)


def MakeInnerTxn(**kwargs: Expr) -> Expr:
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
    return Seq(
        # black: dont-compact-seq
        InnerTxnBuilder.Begin(),
        InnerTxn(**kwargs),
        InnerTxnBuilder.Submit(),
    )


# pylint: disable=unused-argument


def InnerPaymentTxn(
    sender: Optional[Expr] = None,
    receiver: Optional[Expr] = None,
    amount: Optional[Expr] = None,
    close_remainder_to: Optional[Expr] = None,
    fee: Optional[Expr] = None,
) -> InnerTxn:
    """
    Create an inner txn and set provided fields.

    This is equivalent to:
    ```
    Seq(
        InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.Payment),
        InnerTxnBuilder.SetFields([fields provided as arguments]),
    )
    ```
    """
    return InnerTxn(type_enum=TxnType.Payment, **locals())


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


def InnerAssetTransferTxn(
    sender: Optional[Expr] = None,
    asset_receiver: Optional[Expr] = None,
    asset_amount: Optional[Expr] = None,
    xfer_asset: Optional[Expr] = None,
    asset_close_to: Optional[Expr] = None,
    fee: Optional[Expr] = None,
) -> InnerTxn:
    """
    Create an inner txn and set provided fields.

    This is equivalent to:
    ```
    Seq(
        InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.AssetTransfer),
        InnerTxnBuilder.SetFields([fields provided as arguments]),
    )
    ```
    """
    return InnerTxn(type_enum=TxnType.AssetTransfer, **locals())


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


def InnerAssetFreezeTxn(
    sender: Optional[Expr] = None,
    freeze_asset: Optional[Expr] = None,
    freeze_asset_account: Optional[Expr] = None,
    freeze_asset_frozen: Optional[Expr] = None,
    fee: Optional[Expr] = None,
) -> InnerTxn:
    """
    Create an inner txn and set provided fields.

    This is equivalent to:
    ```
    Seq(
        InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.AssetFreeze),
        InnerTxnBuilder.SetFields([fields provided as arguments]),
    )
    ```
    """
    return InnerTxn(type_enum=TxnType.AssetFreeze, **locals())


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


def InnerAssetConfigTxn(
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
) -> InnerTxn:
    """
    Create and execute an inner asset config transaction.

    This is equivalent to:
    ```
    Seq(
        InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.AssetConfig),
        InnerTxnBuilder.SetFields([fields provided as arguments]),
    )
    ```

    Reference: `MakeInnerAssetConfigTxn`
    """
    return InnerTxn(type_enum=TxnType.AssetConfig, **locals())


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


def InnerApplicationCallTxn(
    sender: Optional[Expr] = None,
    application_id: Optional[Expr] = None,
    on_completion: Optional[Expr] = None,
    application_args: Optional[list[Expr]] = None,
    accounts: Optional[list[Expr]] = None,
    applications: Optional[list[Expr]] = None,
    assets: Optional[list[Expr]] = None,
    approval_program: Optional[Expr] = None,
    clear_state_program: Optional[Expr] = None,
    global_num_byte_slices: Optional[Expr] = None,
    global_num_uints: Optional[Expr] = None,
    local_num_byte_slices: Optional[Expr] = None,
    local_num_uints: Optional[Expr] = None,
    extra_program_pages: Optional[Expr] = None,
    fee: Optional[Expr] = None,
) -> InnerTxn:
    """
    Create an inner txn and set provided fields.

    This is equivalent to:
    ```
    Seq(
        InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.ApplicationCall),
        InnerTxnBuilder.SetFields([fields provided as arguments]),
    )
    ```

    Reference: MakeInnerApplicationCallTxn
    """
    return InnerTxn(type_enum=TxnType.ApplicationCall, **locals())


def MakeInnerApplicationCallTxn(
    sender: Optional[Expr] = None,
    application_id: Optional[Expr] = None,
    on_completion: Optional[Expr] = None,
    application_args: Optional[list[Expr]] = None,
    accounts: Optional[list[Expr]] = None,
    applications: Optional[list[Expr]] = None,
    assets: Optional[list[Expr]] = None,
    approval_program: Optional[Expr] = None,
    clear_state_program: Optional[Expr] = None,
    global_num_byte_slices: Optional[Expr] = None,
    global_num_uints: Optional[Expr] = None,
    local_num_byte_slices: Optional[Expr] = None,
    local_num_uints: Optional[Expr] = None,
    extra_program_pages: Optional[Expr] = None,
    fee: Optional[Expr] = None,
) -> Expr:
    """
    Create an inner application call transaction.

    Args:
        sender: The sender's address. Leave it empty and it will be autoset to contract's address.
        application_id: Application ID to be called
        on_completion: The completion code to be executed after the application is called
        application_args: Application arguments
        accounts: Accounts to be used in the application
        applications: Applications to be used in the application
        assets: Assets to be used in the application
        approval_program: Logic executed for every application transaction
        clear_state_program: Logic executed for application transactions with on-completion set to "clear"
        global_num_byte_slices: The maximum number of global byte slices to be used in the application
        global_num_uints: The maximum number of global uints to be used in the application
        local_num_byte_slices: The maximum number of local byte slices to be used in the application
        local_num_uints: The maximum number of local uints to be used in the application
        extra_program_pages: The number of extra program space to be allocated for the created application
        fee: The fee for the transaction in microAlgos

    For more details about parameters needed for your use-case visit:
    https://developer.algorand.org/docs/get-details/transactions/transactions/#application-call-transaction
    """
    return MakeInnerTxn(type_enum=TxnType.ApplicationCall, **locals())


def InnerNoOpTxn(
    sender: Optional[Expr] = None,
    application_id: Optional[Expr] = None,
    application_args: Optional[list[Expr]] = None,
    accounts: Optional[list[Expr]] = None,
    applications: Optional[list[Expr]] = None,
    assets: Optional[list[Expr]] = None,
    fee: Optional[Expr] = None,
) -> InnerTxn:
    """
    Create an inner no op application call txn and set provided fields.
    Convenience function for the most common use-case.

    This is equivalent to:
    ```
    Seq(
        InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.ApplicationCall),
        InnerTxnBuilder.SetField(TxnField.on_completion, OnComplete.NoOp),
        InnerTxnBuilder.SetFields([fields provided as arguments]),
    )
    ```

    Reference: MakeInnerNoOpTxn
    """
    return InnerApplicationCallTxn(on_completion=OnComplete.NoOp, **locals())


def MakeInnerNoOpTxn(
    sender: Optional[Expr] = None,
    application_id: Optional[Expr] = None,
    application_args: Optional[list[Expr]] = None,
    accounts: Optional[list[Expr]] = None,
    applications: Optional[list[Expr]] = None,
    assets: Optional[list[Expr]] = None,
    fee: Optional[Expr] = None,
) -> Expr:
    """
    Create an inner no-op application call transaction.
    Convenience function for the most common type of application call.

    Args:
        sender: The sender's address. Leave it empty and it will be autoset to contract's address.
        application_id: Application ID to be called
        application_args: Application arguments
        accounts: Accounts to be used in the application
        applications: Applications to be used in the application
        assets: Assets to be used in the application
        fee: The fee for the transaction in microAlgos

    For more details about parameters needed for your use-case visit:
    https://developer.algorand.org/docs/get-details/transactions/transactions/#application-call-transaction
    """
    return MakeInnerApplicationCallTxn(on_completion=OnComplete.NoOp, **locals())


def MakeInnerGroupTxn(*txns: InnerTxn) -> Expr:
    """
    Create and execute inner atomic group transaction.

    Each of the transactions' fields will be set in order.
    And the transaction group will be executed afterwards.

    Args:
        txns: list of inner transactions to be executed as part of the group
    """
    for txn in txns:
        if not isinstance(txn, InnerTxn):
            raise ValueError("MakeInnerGroupTxn can only take instances of InnerTxn as parameters")
    steps = []
    for i, txn in enumerate(txns):
        steps.append(txn)
        if i == len(txns) - 1:
            steps.append(InnerTxnBuilder.Submit())
        else:
            steps.append(InnerTxnBuilder.Next())
    return Seq(InnerTxnBuilder.Begin(), *steps)
