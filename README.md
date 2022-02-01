# Pyteal Extensions
Additional useful operations for Python

## Available Operations
- `MulDiv64`: calculate `m1*m2/d` with no overflow on multiplication (TEAL 3+)
- `Min`, `Max`: calculate minimum/maximum of 2 expressions, without using slots or evaluating arguments more than once (TEAL 4+)
- `LazyAnd`, `LazyOr`: lazily evaluate arguments in And/Or operation
- [Inner Transactions](docs/inner_transactions.md): simplified making of inner transactions
    - `MakeInnerPaymentTxn`, `MakeInnerAssetTransferTxn` and more!
- `SerializeIntegers`, `DeserializeIntegers`, `DeserializeIntegersToSlots`: serialize/deserialize integers to/from bytes
- `GlobalState`, `LocalState`, `GlobalStateArray`, `LocalStateArray`: easily access global/local state

### State manipulation
`GlobalState` and `LocalState` allow for manipulating global and local state respectively.
They both have the same interface.
```python
from pyteal import App, Bytes, Int, Seq, TealType
from pytealext import LocalState

user_counter = LocalState("UC", TealType.uint64)
program = Seq(
    # increment using pyteal local state
    App.localPut(Int(0), Bytes("UC"), App.localGet(Int(0), Bytes("UC")) + Int(1)),
    # increment using put/get
    user_counter.put(user_counter.get() + Int(1)),
    # increment using add_assign
    user_counter.add_assign(Int(1))
    # decrement
    user_counter.sub_assign(Int(1))
)
```

Want to simulate arrays in the global state? Use `GlobalStateArray` and `LocalStateArray`.
Technically, the indexes can be any uint64 value and don't have to be sequential.
```python
from pyteal import Assert, For, Int, Return, ScratchVar, Seq
from pytealext import LocalStateArray

user_counters = LocalStateArray("Counters")
    i = ScratchVar()
    accumulator = ScratchVar()
    program = Seq(
        user_counters[0].put(Int(10)),
        user_counters[0].add_assign(Int(1)),
        user_counters[0].sub_assign(Int(2)),
        Assert(user_counters[0].get() == Int(9)),
        # set some other indexes
        user_counters[1].put(Int(9)),
        user_counters[2].put(Int(9)),
        # Indexes can also be accessed with Exprs
        accumulator.store(Int(0)),
        For(i.store(Int(0)), i.load() < Int(3), i.store(i.load() + Int(1))).Do(
            accumulator.store(accumulator.load() + user_counters[i.load()].get())
        ),
        Return(accumulator.load() == Int(27)),
    )
```

## Example usage
Example usage for `LazyAnd`:
```python
from pyteal import Gtxn, TxnType, Bytes, Int
from pytealext import LazyAnd

# Evaluate fields of some transaction but don't panic if an argument down the line would panic
validation = LazyAnd(
    Gtxn[0].type_enum() == TxnType.ApplicationCall,
    Gtxn[0].application_args.length() == Int(1),
    Gtxn[0].application_args[0] == Bytes("AX"),
)
```

## Installation
`pip install pytealext`

## Testing
`pytest`

-------
Created by Łukasz Ptak and Paweł Rejkowicz
