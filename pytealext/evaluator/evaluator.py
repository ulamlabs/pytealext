from math import isqrt
from typing import IO

from algosdk.future.transaction import ApplicationCallTxn

INTEGER_SIZE = 2**64


class Panic(Exception):
    """
    Exception raised when the evaluator encounters an error
    """

    def __init__(self, message, line_number):
        super().__init__(message, f"{line_number=}")
        self.message = message
        self.line_number = line_number


class AssertionFailed(Panic):
    """
    Exception raised when an assertion fails
    """

    def __init__(self, line_number):
        super().__init__("Assert failed", line_number)


MaxLogCalls = 32
MaxLogSize = 1024

MaxLocalStateSize = 16
MaxGlobalStateSize = 64


class EvalContext:
    """
    Class containing the execution environment for an application call
    """

    def __init__(
        self,
        *,
        global_state: dict[bytes, bytes or int] or None = None,
        local_state: dict[bytes, bytes or int] or None = None,
        txn: ApplicationCallTxn or None = None,
    ):
        """
        Args:
            global_state: The global state of the application
            local_state: The local state of the user interacting with the application
            txn: The transaction that is being evaluated
        """
        self.global_state = global_state if global_state is not None else {}  # type: dict[bytes, int or bytes]
        self.local_state = local_state if local_state is not None else {}  # type: dict[bytes, int or bytes]
        self.txn = txn
        self.log = []  # type: list[bytes]


def split128(val: int):
    """
    Splits a 128-bit integer into a tuple (x, y) of 64-bit integers
    where x are the higher 64 bits and y are the lower 64 bits
    """
    return val // INTEGER_SIZE, val % INTEGER_SIZE


def eval_teal(
    lines: list[str],
    return_stack=True,
    context: EvalContext or None = None,
    debug: IO or None = None,
) -> tuple[list, list]:
    """
    Simulate a basic teal program.

    Args:
        lines: list of TEAL program lines
        return_stack: whenther "return" opcode shall return the whole stack, not just the value on top
            This is useful in validating if custom TEAL code produces correct amount of values on stack.
            Moreover, with pyteal v0.8 every compiled program has a "return" at the end,
            this would prevent checking contents of the stack once an algorithm finishes executing.
        context: execution context for the program (this will be updated, should state modification occour)
        debug: descriptor to write to after each program step. Current line as well as
            stack contents before the operation are reported.

    Returns:
        tuple of (stack, slots)
    """
    stack = []  # type: list[int or str]
    slots = [0 for _ in range(256)]
    branch_targets = {
        line[:-1]: nr  # strip trailing ":" from key, ex. b11: -> b11
        for nr, line in enumerate(lines)
        if line[-1] == ":"
    }

    current_line = 0
    while current_line < len(lines):
        line = lines[current_line]
        current_line += 1

        if debug:
            print(f"{current_line}: {line} | {stack}", file=debug)

        if line.startswith("#"):
            continue
        if line[-1] == ":":
            continue

        if line == "return":  # ends eval immediately
            if return_stack:
                return stack, slots
            return [stack[-1]], slots

        line_s = line.split()
        op = line_s[0]
        args = line_s[1:]
        if op == "dup":
            x = stack[-1]
            stack.append(stack[-1])
        elif op == "dup2":
            x = stack[-2], stack[-1]
            stack.extend(x)
        elif op == "pop":
            stack.pop()
        elif op == "mulw":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            ab = a * b
            stack.extend(split128(ab))
        elif op == "addw":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            ab = a + b
            stack.extend(split128(ab))
        elif op == "bitlen":
            a = stack.pop()
            if isinstance(a, bytes):
                a = int.from_bytes(a, "big")
            stack.append(a.bit_length())
        elif op == "divmodw":
            divisor_lo = stack.pop()
            divisor_hi = stack.pop()
            dividend_lo = stack.pop()
            dividend_hi = stack.pop()
            if (
                not isinstance(divisor_lo, int)
                or not isinstance(divisor_hi, int)
                or not isinstance(dividend_lo, int)
                or not isinstance(dividend_hi, int)
            ):
                raise Panic("Invalid type", current_line)
            divisor = divisor_lo + divisor_hi * INTEGER_SIZE
            dividend = dividend_lo + dividend_hi * INTEGER_SIZE
            quotient = dividend // divisor
            remainder = dividend % divisor
            stack.extend(split128(quotient))
            stack.extend(split128(remainder))
        elif op == "|":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            stack.append(a | b)
        elif op == "&":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            stack.append(a & b)
        elif op == "^":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            stack.append(a ^ b)
        elif op == "~":
            a = stack.pop()
            if not isinstance(a, int):
                raise Panic("Invalid type", current_line)
            x = (INTEGER_SIZE - 1) ^ a
            stack.append(x)
        elif op == "shl":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            stack.append(a << b % 2**64)
        elif op == "shr":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            stack.append(a >> b)
        elif op == "sqrt":
            a = stack.pop()
            if not isinstance(a, int):
                raise Panic("Invalid type", current_line)
            stack.append(isqrt(a))
        elif op == "assert":
            a = stack.pop()
            if not isinstance(a, int):
                raise Panic("Invalid type", current_line)
            if a == 0:
                raise AssertionFailed(current_line)
        elif op == "/":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            if not b:
                raise Panic("Division by zero", current_line)
            x = a // b
            stack.append(x)
        elif op == "%":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            if not b:
                raise Panic("Division by zero", current_line)
            x = a % b
            stack.append(x)
        elif op == "!":
            a = stack.pop()
            if not isinstance(a, int):
                raise Panic("Invalid type", current_line)
            x = int(not a)
            stack.append(x)
        elif op == "+":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            if a + b >= INTEGER_SIZE:
                raise Panic("Overflow", current_line)
            x = a + b
            stack.append(x)
        elif op == "-":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            if a - b < 0:
                raise Panic("Underflow", current_line)
            x = a - b
            stack.append(x)
        elif op == "*":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            if a * b >= INTEGER_SIZE:
                raise Panic("Overflow", current_line)
            x = a * b
            stack.append(x)
        elif op == "&&":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            if a and b:
                stack.append(1)
            else:
                stack.append(0)
        elif op == "||":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            if a or b:
                stack.append(1)
            else:
                stack.append(0)
        elif op == ">":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            stack.append(int(bool(a > b)))
        elif op == ">=":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            stack.append(int(bool(a >= b)))
        elif op == "<":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            stack.append(int(bool(a < b)))
        elif op == "<=":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            stack.append(int(bool(a <= b)))
        elif op == "==":
            b = stack.pop()
            a = stack.pop()
            if type(a) is not type(b):
                raise Panic("Type mismatch", current_line)
            stack.append(int(bool(a == b)))
        elif op == "!=":
            b = stack.pop()
            a = stack.pop()
            if type(a) is not type(b):
                raise Panic("Type mismatch", current_line)
            stack.append(int(bool(a != b)))
        elif op == "select":
            c = stack.pop()
            b = stack.pop()
            a = stack.pop()
            if not isinstance(c, int):
                raise Panic("Invalid types", current_line)
            if c != 0:
                stack.append(b)
            else:
                stack.append(a)
        elif op == "swap":
            b = stack.pop()
            a = stack.pop()
            stack.append(b)
            stack.append(a)
        elif op == "app_global_get":
            key = stack.pop()
            if context is None:
                raise Exception("app_global_get requires execution environment context")
            val = context.global_state.get(key, 0)
            stack.append(val)
        elif op == "app_global_put":
            b = stack.pop()
            a = stack.pop()
            if context is None:
                raise Exception("app_global_put requires execution environment context")
            context.global_state[a] = b
            if len(context.global_state) > MaxGlobalStateSize:
                raise Panic("Global state size exceeded", current_line)
        elif op == "app_local_get":
            b = stack.pop()
            a = stack.pop()
            if a != 0:
                raise Panic("app_local_get is only supported with 0 as the account parameter", current_line)
            if not isinstance(b, bytes):
                raise Panic("app_local_get key must be a bytes value", current_line)
            stack.append(context.local_state.get(b, 0))
        elif op == "app_local_put":
            c = stack.pop()
            b = stack.pop()
            a = stack.pop()
            if a != 0:
                raise Panic("app_local_put is only supported with 0 as the account parameter", current_line)
            if not isinstance(b, bytes):
                raise Panic("app_local_put key must be a bytes value", current_line)
            context.local_state[b] = c
            if len(context.local_state) > MaxLocalStateSize:
                raise Panic("Local state size exceeded", current_line)
        elif op == "log":
            val = stack.pop()
            if not isinstance(val, bytes):
                raise Panic("log requires bytes value", current_line)
            if context is None:
                raise Exception("log requires execution environment context")
            context.log.append(val)
            if sum(len(l) for l in context.log) > MaxLogSize:
                raise Panic("log size limit exceeded", current_line)
            if len(context.log) > MaxLogCalls:
                raise Panic("log calls limit exceeded", current_line)
        elif op == "itob":
            val = stack.pop()
            if not isinstance(val, int):
                raise Panic("itob requires integer value", current_line)
            val = val.to_bytes(8, "big")
            stack.append(val)
        elif op == "btoi":
            val = stack.pop()
            if not isinstance(val, bytes):
                raise Panic("btoi requires bytes value", current_line)
            if len(val) > 8:
                raise Panic("btoi requires bytes of length 8 or less", current_line)
            val = int.from_bytes(val, "big")
            stack.append(val)
        elif op == "concat":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, bytes) or not isinstance(b, bytes):
                raise Panic("Invalid type", current_line)
            stack.append(a + b)
        elif op == "extract3":
            c = stack.pop()
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, bytes) or not isinstance(b, int) or not isinstance(c, int):
                raise Panic("Invalid type", current_line)
            stack.append(a[b : b + c])
        elif op == "extract":
            a = stack.pop()
            start = int(args[0])
            length = int(args[1])
            if not isinstance(a, bytes):
                raise Panic("Invalid type", current_line)
            if start < 0 or length < 0 or start + length > len(a):
                raise Panic("Invalid slice", current_line)
            stack.append(a[start : start + length])
        elif op == "extract_uint16":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, bytes) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            if b + 2 > len(a):
                raise Panic("Out of bounds", current_line)
            stack.append(int.from_bytes(a[b : b + 2], "big"))
        elif op == "extract_uint32":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, bytes) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            if b + 4 > len(a):
                raise Panic("Out of bounds", current_line)
            stack.append(int.from_bytes(a[b : b + 4], "big"))
        elif op == "extract_uint64":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, bytes) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            if b + 8 > len(a):
                raise Panic("Out of bounds", current_line)
            stack.append(int.from_bytes(a[b : b + 8], "big"))
        # provisional support for txna
        elif op == "txna":
            if args[0] == "ApplicationArgs":
                arg_index = int(args[1])
                if arg_index > len(context.txn.app_args):
                    raise Panic("txna ApplicationArgs index out of bounds", current_line)
                stack.append(context.txn.app_args[arg_index])
            else:
                raise Exception("Unsupported txna expression")
        elif op == "byte":
            arg = args[0]
            if arg[0] == '"' and arg[-1] == '"':
                arg = arg[1:-1]  # strip quotes
                arg = arg.encode("utf-8")
            elif arg.startswith("0x"):
                arg = arg[2:]
                arg = bytes.fromhex(arg)
            else:
                raise Panic("byte requires string or hex value", current_line)
            stack.append(arg)
        elif op == "int":
            x = int(args[0])
            if x < 0 or x >= INTEGER_SIZE:
                raise Panic(
                    f"int expects non-negative integer smaller than {INTEGER_SIZE} (actual={x})",
                    current_line,
                )
            stack.append(x)
        elif op == "bnz":
            cond = stack.pop()
            if cond != 0:
                current_line = branch_targets[args[0]]
        elif op == "bz":
            cond = stack.pop()
            if cond == 0:
                current_line = branch_targets[args[0]]
        elif op == "b":
            current_line = branch_targets[args[0]]
        elif op == "cover":
            nr = int(args[0])
            top = stack.pop()
            if nr > len(stack):
                raise Panic(f"cover {nr} with stack size {len(stack)}", current_line)
            stack.insert(-nr, top)
        elif op == "store":
            i = int(args[0])
            x = stack.pop()
            slots[i] = x
        elif op == "load":
            i = int(args[0])
            x = slots[i]
            stack.append(x)
        else:
            raise Exception(f"Operation '{line}' is not supported by the simulator")
    return stack, slots
