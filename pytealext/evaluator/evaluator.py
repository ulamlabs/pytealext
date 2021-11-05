INTEGER_SIZE = 2 ** 64


class Panic(Exception):
    """
    Exception raised when the evaluator encounters an error
    """

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class AssertionFailed(Panic):
    """
    Exception raised when an assertion fails
    """

    def __init__(self):
        super().__init__("Assert failed")


MaxLogCalls = 32
MaxLogSize = 1024


class EvalContext:
    """
    Class containing the execution environment for an application call
    """

    def __init__(self, global_state: dict[bytes, bytes or int] or None = None):
        self.global_state = global_state if global_state is not None else {}  # type: dict[bytes, int or bytes]
        self.log = []  # type: list[bytes]


def split128(val: int):
    """
    Splits a 128-bit integer into a tuple (x, y) of 64-bit integers
    where x are the higher 64 bits and y are the lower 64 bits
    """
    return val // INTEGER_SIZE, val % INTEGER_SIZE


def eval_teal(lines: list[str], return_stack=True, context: EvalContext or None = None) -> tuple[list, list]:
    """
    Simulate a basic teal program.

    Args:
        lines: list of TEAL program lines
        return_stack: whenther "return" opcode shall return the whole stack, not just the value on top
            This is useful in validating if custom TEAL code produces correct amount of values on stack.
            Moreover, with pyteal v0.8 every compiled program has a "return" at the end,
            this would prevent checking contents of the stack once an algorithm finishes executing.
        context: execution context for the program (this will be updated, should state modification occour)

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

        if line.startswith("#"):
            continue
        if line[-1] == ":":
            continue

        if line == "return":  # ends eval immediately
            if return_stack:
                return stack, slots
            return [stack[-1]], slots
        if line == "dup":
            x = stack[-1]
            stack.append(stack[-1])
        elif line == "dup2":
            x = stack[-2], stack[-1]
            stack.extend(x)
        elif line == "pop":
            stack.pop()
        elif line == "mulw":
            b = stack.pop()
            a = stack.pop()
            ab = a * b
            stack.extend(split128(ab))
        elif line == "addw":
            b = stack.pop()
            a = stack.pop()
            ab = a + b
            stack.extend(split128(ab))
        elif line == "divmodw":
            divisor_lo = stack.pop()
            divisor_hi = stack.pop()
            dividend_lo = stack.pop()
            dividend_hi = stack.pop()
            divisor = divisor_lo + divisor_hi * INTEGER_SIZE
            dividend = dividend_lo + dividend_hi * INTEGER_SIZE
            quotient = dividend // divisor
            reminder = dividend % divisor
            stack.extend(split128(quotient))
            stack.extend(split128(reminder))
        elif line == "assert":
            val = stack.pop()
            if val == 0:
                raise AssertionFailed
        elif line == "/":
            b = stack.pop()
            a = stack.pop()
            if not b:
                raise Panic
            x = a // b
            stack.append(x)
        elif line == "%":
            b = stack.pop()
            a = stack.pop()
            if not b:
                raise Panic
            x = a % b
            stack.append(x)
        elif line == "!":
            a = stack.pop()
            x = int(not a)
            stack.append(x)
        elif line == "~":
            a = stack.pop()
            x = (INTEGER_SIZE - 1) ^ a
            stack.append(x)
        elif line == "+":
            b = stack.pop()
            a = stack.pop()
            if a + b >= INTEGER_SIZE:
                raise Panic("Overflow")
            x = a + b
            stack.append(x)
        elif line == "-":
            b = stack.pop()
            a = stack.pop()
            if a - b < 0:
                raise Panic("Underflow")
            x = a - b
            stack.append(x)
        elif line == "*":
            b = stack.pop()
            a = stack.pop()
            if a * b >= INTEGER_SIZE:
                raise Panic("Overflow")
            x = a * b
            stack.append(x)
        elif line == "&&":
            b = stack.pop()
            a = stack.pop()
            if a and b:
                stack.append(1)
            else:
                stack.append(0)
        elif line == "||":
            b = stack.pop()
            a = stack.pop()
            if a or b:
                stack.append(1)
            else:
                stack.append(0)
        elif line == ">":
            b = stack.pop()
            a = stack.pop()
            stack.append(int(bool(a > b)))
        elif line == "<":
            b = stack.pop()
            a = stack.pop()
            stack.append(int(bool(a < b)))
        elif line == "select":
            c = stack.pop()
            b = stack.pop()
            a = stack.pop()
            if c != 0:
                stack.append(b)
            else:
                stack.append(a)
        elif line == "swap":
            b = stack.pop()
            a = stack.pop()
            stack.append(b)
            stack.append(a)
        elif line == "app_global_get":
            key = stack.pop()
            if context is None:
                raise Exception("app_global_get requires execution environment context")
            val = context.global_state.get(key, 0)
            stack.append(val)
        elif line == "app_global_put":
            b = stack.pop()
            a = stack.pop()
            if context is None:
                raise Exception("app_global_put requires execution environment context")
            context.global_state[a] = b
        elif line == "log":
            val = stack.pop()
            if not isinstance(val, bytes):
                raise Panic("log requires bytes value")
            if context is None:
                raise Exception("log requires execution environment context")
            context.log.append(val)
            if sum(len(l) for l in context.log) > MaxLogSize:
                raise Panic("log size limit exceeded")
            if len(context.log) > MaxLogCalls:
                raise Panic("log calls limit exceeded")
        elif line == "itob":
            val = stack.pop()
            if not isinstance(val, int):
                raise Panic("itob requires integer value")
            val = val.to_bytes(8, "big")
            stack.append(val)
        elif line == "btoi":
            val = stack.pop()
            if not isinstance(val, bytes):
                raise Panic("btoi requires bytes value")
            val = int.from_bytes(val, "big")
            stack.append(val)
        elif " " in line:
            op, arg = line.split(" ")
            if op == "byte":
                if arg[0] != '"' or arg[-1] != '"':
                    raise Exception("byte expects string literal (this is a very basic evaluator)")
                arg = arg[1:-1]  # strip quotes
                stack.append(arg.encode("utf-8"))
            elif op == "int":
                x = int(arg)
                stack.append(x)
            elif op == "bnz":
                cond = stack.pop()
                if cond != 0:
                    current_line = branch_targets[arg]
            elif op == "bz":
                cond = stack.pop()
                if cond == 0:
                    current_line = branch_targets[arg]
            elif op == "b":
                current_line = branch_targets[arg]
            elif op == "cover":
                nr = int(arg)  # get the number after the space
                top = stack.pop()
                if nr > len(stack):
                    raise Panic(f"cover {nr} with stack size {len(stack)}")
                stack.insert(-nr, top)
            else:
                if op == "store":
                    i = int(arg)
                    x = stack.pop()
                    slots[i] = x
                elif op == "load":
                    i = int(arg)
                    x = slots[i]
                    stack.append(x)
                else:
                    raise Exception(f"Operation '{line}' is not supported by the simulator")
        else:
            raise Exception(f"Operation '{line}' is not supported by the simulator")
    return stack, slots
