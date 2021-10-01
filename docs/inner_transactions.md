# Inner transactions

## Example use
```python
from pyteal import *
from pytealext import MakeInnerAssetTransferTxn

asset_id_to_distribute = 12345

# smart contract
faucet_program = Seq(
    MakeInnerAssetTransferTxn(
        asset_receiver=Txn.sender(),
        asset_amount=Int(1000),
        xfer_asset=Int(0)  # will distribute asset with ID provided in Txn.assets[0]
    )
)
```

## Combining with subroutines
If you're using a certain template for transfers in your app or making a lot of transfers, you may consider wrapping MakeInner*Txn into a Subroutine

```python
from pyteal import *
from pytealext import MakeInnerAssetTransferTxn

ASSET_ID = 1234
PARASITE_ADDRESS = "SomeAddress..."

@Subroutine(TealType.none)
def SimpleAssetTransfer(receiver: Expr, amount: Expr):
    return MakeInnerAssetTransfer(
        asset_receiver=receiver,
        asset_amount=amount,
        xfer_asset=Int(ASSET_ID),  # this ID must be present in Txn.assets!
        fee=Int(0),  # The fee must be pooled, we don't want our contract to pay for the inner Txn
    )

# a piece of program which sends the creator 10000 units of an asset but also send a small amount to another address
program_piece = Seq(
    Assert(Txn.sender() == Global.creator_address()),
    SimpleAssetTransfer(Txn.sender(), Int(10000)),
    SimpleAssetTransfer(Addr(PARASITE_ADDRESS), Int(10))
)
```
