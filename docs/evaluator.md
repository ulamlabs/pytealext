# Eval TEAL examples

1. Quickly evaluate expression's integer value
```python
from pyteal import *
from pytealext.evaluator import compile_and_run

expr = Exp(Int(2), Int(23)) + Int(1)

stack, slots = compile_and_run(expr)

assert stack[0] == 2**23+1
```

2. Capture a bytes value
```python
# PyTEAL's compileTeal doesn't allow returning bytes from the main program
# We can work around this by using a scratch variable.
from pyteal import *
from pytealext.evaluator import compile_and_run

result = ScratchVar(slotId=0)  # set the slotId so we can read it later

expr = Seq(
    result.store(Bytes("Hello, world!")),
    Int(1)  # simply return success
)

stack, slots = compile_and_run(expr)

assert stack == [1]
assert slots[0] == b"Hello, world!"
```

3. Decode a big integer
```python
# The technique above can be used with a big integer
# Decode it after evaluation:

res_big_int = slots[0]
res_big_int = int.from_bytes(res_big_int, byteorder="big")
```