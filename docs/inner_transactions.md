# Inner transactions

## Example use
### Algo faucet
```python
from pyteal import *
from pytealext import MakeInnerPaymentTxn

# smart contract
faucet_program = Seq(
    MakeInnerPaymentTxn(
        receiver=Txn.sender(),
        amount=Int(1000),
        fee=Int(0),
    )
)
```

### Opt-in contract to ASA
```python
from pyteal import *
from pytealext import MakeInnerAssetTransferTxn

AMAZING_COIN_ID = 123456

# smart contract
faucet_program = Seq(
    MakeInnerAssetTransferTxn(
        asset_receiver=Global.current_application_address(),
        asset_amount=Int(0),
        xfer_asset=Int(AMAZING_COIN_ID),  # Txn.assets must contain this ID!
        # fee=Int(0),  # uncomment to specify that the fee must be pooled
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
    return MakeInnerAssetTransferTxn(
        asset_receiver=receiver,
        asset_amount=amount,
        xfer_asset=Int(ASSET_ID),  # this ID must be present in Txn.assets!
        fee=Int(0),  # The fee must be pooled, we don't want our contract to pay for the inner Txn
    )

# a piece of program which sends the creator 10000 units of an asset but also sends a small amount to another address
program_piece = Seq(
    Assert(Txn.sender() == Global.creator_address()),
    SimpleAssetTransfer(Txn.sender(), Int(10000)),
    SimpleAssetTransfer(Addr(PARASITE_ADDRESS), Int(10))
)
```
