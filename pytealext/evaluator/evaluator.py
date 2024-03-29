from dataclasses import dataclass
from math import isqrt
from typing import IO

from algosdk.encoding import decode_address
from algosdk.transaction import ApplicationCallTxn

INTEGER_SIZE = 2**64


def int_to_trimmed_bytes(value: int) -> bytes:
    """Convert an integer into a big-endian byte array with no leading zero bytes

    Special case: zero is converted to a single zero byte
    """
    byte_length = (value.bit_length() + 7) // 8
    byte_length = max(1, byte_length)  # handle zero special case
    return value.to_bytes(byte_length, "big")


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


class EvaluatorError(Panic):
    """Exception class used when the evauator encounters an error caused by improper use of the evaluator.

    This also includes errors from unimplemented features.
    """


MaxLogCalls = 32
MaxLogSize = 1024
MaxStringSize = 4096

MaxLocalStateSize = 16
MaxGlobalStateSize = 64


class EvalContext:  # pylint: disable=too-few-public-methods
    """
    Class containing the execution environment for an application call
    """

    def __init__(
        self,
        *,
        global_state: dict[bytes, bytes | int] | None = None,
        local_state: dict[bytes, bytes | int] | None = None,
        txn: ApplicationCallTxn | None = None,
    ):
        """
        Args:
            global_state: The global state of the application
            local_state: The local state of the user interacting with the application
            txn: The transaction that is being evaluated
        """
        self.global_state: dict[bytes, int | bytes] = global_state if global_state is not None else {}
        self.local_state: dict[bytes, int | bytes] = local_state if local_state is not None else {}
        self.txn = txn
        self.log: list[bytes] = []


@dataclass
class Frame:
    """A call frame"""

    ret_line: int
    height: int
    clear: bool = False  # should retsub clear the stack after returning from proto function
    argc: int = 0  # argument count
    retc: int = 0  # return values count


def split128(val: int):
    """
    Splits a 128-bit integer into a tuple (x, y) of 64-bit integers
    where x are the higher 64 bits and y are the lower 64 bits
    """
    return val // INTEGER_SIZE, val % INTEGER_SIZE


def eval_teal(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    lines: list[str] | str,
    return_stack=True,
    context: EvalContext | None = None,
    debug: IO | None = None,
) -> tuple[list, list]:
    """
    Simulate a basic teal program.

    Args:
        lines: list of TEAL program lines or compiled program string
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
    if isinstance(lines, str):
        lines = lines.splitlines()
    if not isinstance(lines, list):
        raise TypeError("lines must be a list of strings or a string")

    stack: list[int | bytes] = []
    call_stack: list[Frame] = []
    slots: list[int | bytes] = [0 for _ in range(256)]
    branch_targets = {
        line[:-1]: nr  # strip trailing ":" from key, ex. b11: -> b11
        for nr, line in enumerate(lines)
        if line and line[-1] == ":"
    }

    current_line = 0
    op = "eval_teal__empty_opcode"  # current opcode

    while current_line < len(lines):
        line = lines[current_line]
        current_line += 1

        if debug:
            print(f"{current_line}: {line} | {stack}", file=debug)

        if line.startswith("#"):
            continue
        if not line:
            continue
        if line[-1] == ":":
            continue

        if line == "return":  # ends eval immediately
            if return_stack:
                return stack, slots
            return [stack[-1]], slots

        line_s = line.split()
        prev_op = op
        op = line_s[0]
        args = line_s[1:]
        res: int | bytes  # defined here to satisfy mypy
        x: int | bytes  # defined here to satisfy mypy
        if op == "err":
            raise Panic("Encountered error opcode", current_line)
        if op == "dup":
            stack.append(stack[-1])
        elif op == "dup2":
            stack.extend((stack[-2], stack[-1]))
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
        elif op == "exp":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int):
                raise Panic("Invalid type", current_line)
            if a**b > INTEGER_SIZE:
                raise Panic("Overflow", current_line)
            if a == 0 and b == 0:
                raise Panic("Invalid input", current_line)
            stack.append(a**b)
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
        elif op == "b+":
            b = stack.pop()
            a = stack.pop()
            if type(a) is not type(b):
                raise Panic("Type mismatch", current_line)
            if not isinstance(a, bytes) or not isinstance(b, bytes):
                raise Panic("Invalid type", current_line)
            if len(a) > 64 or len(b) > 64:
                raise Panic("Bytes overflow", current_line)
            stack.append(int_to_trimmed_bytes(int.from_bytes(a, "big") + int.from_bytes(b, "big")))
        elif op == "b-":
            b = stack.pop()
            a = stack.pop()
            if type(a) is not type(b):
                raise Panic("Type mismatch", current_line)
            if not isinstance(a, bytes) or not isinstance(b, bytes):
                raise Panic("Invalid type", current_line)
            if len(a) > 64 or len(b) > 64:
                raise Panic("Bytes overflow", current_line)
            if int.from_bytes(a, "big") - int.from_bytes(b, "big") < 0:
                raise Panic("Underflow", current_line)
            stack.append(int_to_trimmed_bytes(int.from_bytes(a, "big") - int.from_bytes(b, "big")))
        elif op == "b/":
            b = stack.pop()
            a = stack.pop()
            if type(a) is not type(b):
                raise Panic("Type mismatch", current_line)
            if not isinstance(a, bytes) or not isinstance(b, bytes):
                raise Panic("Invalid type", current_line)
            if len(a) > 64 or len(b) > 64:
                raise Panic("Bytes overflow", current_line)
            if int.from_bytes(b, "big") == 0:
                raise Panic("Division by 0", current_line)
            stack.append(int_to_trimmed_bytes(int.from_bytes(a, "big") // int.from_bytes(b, "big")))
        elif op == "b*":
            b = stack.pop()
            a = stack.pop()
            if type(a) is not type(b):
                raise Panic("Type mismatch", current_line)
            if not isinstance(a, bytes) or not isinstance(b, bytes):
                raise Panic("Invalid type", current_line)
            if len(a) > 64 or len(b) > 64:
                raise Panic("Bytes overflow", current_line)
            stack.append(int_to_trimmed_bytes(int.from_bytes(a, "big") * int.from_bytes(b, "big")))
        elif op == "b==":
            b = stack.pop()
            a = stack.pop()
            if type(a) is not type(b):
                raise Panic("Type mismatch", current_line)
            if not isinstance(a, bytes) or not isinstance(b, bytes):
                raise Panic("Invalid type", current_line)
            if len(a) > 64 or len(b) > 64:
                raise Panic("Bytes overflow", current_line)
            stack.append(int(bool(int.from_bytes(a, "big") == int.from_bytes(b, "big"))))
        elif op == "b!=":
            b = stack.pop()
            a = stack.pop()
            if type(a) is not type(b):
                raise Panic("Type mismatch", current_line)
            if not isinstance(a, bytes) or not isinstance(b, bytes):
                raise Panic("Invalid type", current_line)
            if len(a) > 64 or len(b) > 64:
                raise Panic("Bytes overflow", current_line)
            stack.append(int(bool(int.from_bytes(a, "big") != int.from_bytes(b, "big"))))
        elif op == "b<":
            b = stack.pop()
            a = stack.pop()
            if type(a) is not type(b):
                raise Panic("Type mismatch", current_line)
            if not isinstance(a, bytes) or not isinstance(b, bytes):
                raise Panic("Invalid type", current_line)
            if len(a) > 64 or len(b) > 64:
                raise Panic("Bytes overflow", current_line)
            stack.append(int(bool(int.from_bytes(a, "big") < int.from_bytes(b, "big"))))
        elif op == "b<=":
            b = stack.pop()
            a = stack.pop()
            if type(a) is not type(b):
                raise Panic("Type mismatch", current_line)
            if not isinstance(a, bytes) or not isinstance(b, bytes):
                raise Panic("Invalid type", current_line)
            if len(a) > 64 or len(b) > 64:
                raise Panic("Bytes overflow", current_line)
            stack.append(int(bool(int.from_bytes(a, "big") <= int.from_bytes(b, "big"))))
        elif op == "b>":
            b = stack.pop()
            a = stack.pop()
            if type(a) is not type(b):
                raise Panic("Type mismatch", current_line)
            if not isinstance(a, bytes) or not isinstance(b, bytes):
                raise Panic("Invalid type", current_line)
            if len(a) > 64 or len(b) > 64:
                raise Panic("Bytes overflow", current_line)
            stack.append(int(bool(int.from_bytes(a, "big") > int.from_bytes(b, "big"))))
        elif op == "b>=":
            b = stack.pop()
            a = stack.pop()
            if type(a) is not type(b):
                raise Panic("Type mismatch", current_line)
            if not isinstance(a, bytes) or not isinstance(b, bytes):
                raise Panic("Invalid type", current_line)
            if len(a) > 64 or len(b) > 64:
                raise Panic("Bytes overflow", current_line)
            stack.append(int(bool(int.from_bytes(a, "big") >= int.from_bytes(b, "big"))))
        elif op == "bsqrt":
            a = stack.pop()
            if not isinstance(a, bytes):
                raise Panic("Invalid type", current_line)
            if len(a) > 64:
                raise Panic("Bytes overflow", current_line)
            stack.append(int_to_trimmed_bytes(isqrt(int.from_bytes(a, "big"))))
        elif op == "divw":
            c = stack.pop()
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int) or not isinstance(b, int) or not isinstance(c, int):
                raise Panic("All arguments to divw must be integers", current_line)
            res = (a * INTEGER_SIZE + b) // c
            if res >= INTEGER_SIZE:
                raise Panic("Division overflow", current_line)
            stack.append(res)
        elif op == "bzero":
            a = stack.pop()
            if not isinstance(a, int):
                raise Panic("Invalid type", current_line)
            if a > MaxStringSize:
                raise Panic("Produced byte array would be too long", current_line)
            stack.append(b"\x00" * a)
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
                raise EvaluatorError("app_global_get requires execution environment context", current_line)
            if not isinstance(key, bytes):
                raise Panic("app_global_get key must be a bytes value", current_line)
            val = context.global_state.get(key, 0)
            stack.append(val)
        elif op == "app_global_get_ex":
            key = stack.pop()
            app = stack.pop()
            if context is None:
                raise EvaluatorError("app_global_get_ex requires execution environment context", current_line)
            if app != 0:
                raise EvaluatorError("Accessing other app's global state is unsupported", current_line)
            if not isinstance(key, bytes):
                raise Panic("app_global_get_ex key must be a bytes value", current_line)
            val = context.global_state.get(key, 0)
            exists = int(key in context.global_state)
            stack.append(val)
            stack.append(exists)
        elif op == "app_global_put":
            b = stack.pop()
            a = stack.pop()
            if context is None:
                raise EvaluatorError("app_global_put requires execution environment context", current_line)
            if not isinstance(a, bytes):
                raise Panic("app_global_put key must be a bytes value", current_line)
            context.global_state[a] = b
            if len(context.global_state) > MaxGlobalStateSize:
                raise Panic("Global state size exceeded", current_line)
        elif op == "app_local_get":
            b = stack.pop()
            a = stack.pop()
            if context is None:
                raise EvaluatorError("app_local_get requires execution environment context", current_line)
            if a != 0:
                raise EvaluatorError(
                    "app_local_get is only supported with 0 as the account parameter",
                    current_line,
                )
            if not isinstance(b, bytes):
                raise Panic("app_local_get key must be a bytes value", current_line)
            stack.append(context.local_state.get(b, 0))
        elif op == "app_local_get_ex":
            key = stack.pop()
            app = stack.pop()
            account = stack.pop()
            if context is None:
                raise EvaluatorError("app_local_get_ex requires execution environment context", current_line)
            if app != 0 or account != 0:
                raise EvaluatorError(
                    "app_local_get_ex is only supported with 0 as the account and application parameter", current_line
                )
            if not isinstance(key, bytes):
                raise Panic("app_local_get_ex key must be a bytes value", current_line)
            val = context.local_state.get(key, 0)
            exists = int(key in context.local_state)
            stack.append(val)
            stack.append(exists)
        elif op == "app_local_put":
            c = stack.pop()
            b = stack.pop()
            a = stack.pop()
            if context is None:
                raise EvaluatorError("app_local_put requires execution environment context", current_line)
            if a != 0:
                raise Panic(
                    "app_local_put is only supported with 0 as the account parameter",
                    current_line,
                )
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
                raise EvaluatorError("log requires execution environment context", current_line)
            context.log.append(val)
            if sum(len(log) for log in context.log) > MaxLogSize:
                raise Panic("log size limit exceeded", current_line)
            if len(context.log) > MaxLogCalls:
                raise Panic("log calls limit exceeded", current_line)
        elif op == "len":
            val = stack.pop()
            if not isinstance(val, bytes):
                raise Panic("len requires bytes value", current_line)
            stack.append(len(val))
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
            if len(a) + len(b) > MaxStringSize:
                raise Panic("Produced byte array is too long", current_line)
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
        elif op == "replace2":
            start_position = int(args[0])
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, bytes) or not isinstance(b, bytes):
                raise Panic("Invalid type", current_line)
            if start_position + len(b) > len(a):
                raise Panic("Out of bounds", current_line)
            res = a[:start_position] + b + a[start_position + len(b) :]
            stack.append(res)
        elif op == "replace3":
            c = stack.pop()
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, bytes) or not isinstance(b, int) or not isinstance(c, bytes):
                raise Panic("Invalid type", current_line)
            if b + len(c) > len(a):
                raise Panic("Out of bounds", current_line)
            res = a[:b] + c + a[b + len(c) :]
            stack.append(res)
        # provisional support for txna
        elif op == "txna":
            if context is None:
                raise EvaluatorError("txna requires execution environment context", current_line)
            if context.txn is None:
                raise EvaluatorError("txna requires app call txn to be specified in EvalContext", current_line)
            if args[0] == "ApplicationArgs":
                arg_index = int(args[1])
                if arg_index > len(context.txn.app_args):
                    raise Panic("txna ApplicationArgs index out of bounds", current_line)
                stack.append(context.txn.app_args[arg_index])
            else:
                raise EvaluatorError("Unsupported txna expression", current_line)
        elif op == "addr":
            arg = args[0]
            stack.append(decode_address(arg))
        elif op == "byte":
            arg = line[5:]
            if arg[0] == '"' and arg[-1] == '"':
                arg = arg[1:-1]  # strip quotes
                encoded = arg.encode("utf-8")
            elif arg.startswith("0x"):
                arg = arg[2:]
                encoded = bytes.fromhex(arg)
            else:
                raise Panic("byte requires string or hex value", current_line)
            stack.append(encoded)
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
        elif op == "callsub":
            call_stack.append(Frame(current_line, len(stack)))
            current_line = branch_targets[args[0]]
        elif op == "retsub":
            if len(call_stack) == 0:
                raise Panic("retsub with empty call stack", current_line)
            frame = call_stack.pop()
            if frame.clear:
                expect = frame.height + frame.retc
                if len(stack) < expect:
                    raise Panic(
                        f"retsub with stack size {len(stack)} but expected at least {expect}",
                        current_line,
                    )
                argstart = frame.height - frame.argc
                bottom_stack = stack[:argstart]
                returns = stack[frame.height : expect]
                stack = bottom_stack + returns

            current_line = frame.ret_line
        elif op == "proto":
            if prev_op != "callsub":
                raise Panic("proto must only be used after callsub", current_line)
            if len(stack) < int(args[0]):
                raise Panic(
                    f"proto with stack size {len(stack)} but expected at least {args[0]}",
                    current_line,
                )
            call_stack[-1].argc = int(args[0])
            call_stack[-1].retc = int(args[1])
            call_stack[-1].clear = True
        elif op in ("frame_dig", "frame_bury"):
            arg_slot = int(args[0])  # should be negative
            if len(call_stack) == 0:
                raise Panic("frame_dig with empty call stack", current_line)
            frame = call_stack[-1]
            if frame.clear and -arg_slot > frame.argc:
                raise Panic(
                    f"frame_dig with arg_slot {arg_slot} but argc {frame.argc}",
                    current_line,
                )
            index = frame.height + arg_slot
            if index < 0 or index >= len(stack):
                raise Panic(
                    f"index {index} out of stack bounds [0,{len(stack)}]",
                    current_line,
                )
            if op == "frame_dig":
                stack.append(stack[index])
            else:  # bury
                if index == len(stack) - 1:
                    raise Panic("frame_bury with index on top of stack", current_line)
                stack[index] = stack.pop()
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
        elif op == "stores":
            b = stack.pop()
            a = stack.pop()
            if not isinstance(a, int):
                raise Panic("stores expects integer slot ID", current_line)
            slots[a] = b
        elif op == "loads":
            a = stack.pop()
            if not isinstance(a, int):
                raise Panic("loads expects integer slot ID", current_line)
            stack.append(slots[a])
        else:
            raise EvaluatorError(f"Operation '{line}' is not supported by the simulator", current_line)
    return stack, slots
