# Pyteal Extensions
Additional useful operations for Python

## Available Operations
- `MulDiv64`: calculate `m1*m2/d` with no overflow on multiplication (TEAL 3+)
- `Min`, `Max`: calculate minimum/maximum of 2 expressions, without using slots or evaluating arguments more than once (TEAL 4+)
- `LazyAnd`, `LazyOr`: lazily evaluate arguments in And/Or operation

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

## Testing
`pytest`

-------
Created by Łukasz Ptak and Paweł Rejkowicz
