from dataclasses import dataclass

from .data import OP_COSTS


@dataclass
class ExecutionSummary:
    """
    A summary of the execution of a TEAL expression.
    """

    opcode_usage: dict[str, int]
    call_count: dict[str, int]  # counts how many times the specific branch was taken
    execution_cost: int = 0

    def add_call(self, branch_name: str):
        """Increment the call count for the given branch name."""
        if self.call_count.get(branch_name, 0) == 0:
            self.call_count[branch_name] = 1
        else:
            self.call_count[branch_name] += 1

    def add_opcode(self, opcode: str):
        """Increment the opcode usage for the given opcode."""
        if self.opcode_usage.get(opcode, 0) == 0:
            self.opcode_usage[opcode] = 1
        else:
            self.opcode_usage[opcode] += 1
        try:
            self.execution_cost += OP_COSTS[opcode]()
        except KeyError:
            # these pseudoops will have cost of 1 in compiled code
            # However the total may not be accurate due to usage of intcblock and bytecblock
            if opcode in ("int", "byte", "addr"):
                self.execution_cost += 1
            else:
                raise


def summarize_execution(execution_log: str) -> ExecutionSummary:
    """Summarize the opcode usage in the execution_log

    Args:
        execution_log: the output from eval_teal debug output
    """
    summary = ExecutionSummary(opcode_usage={}, call_count={})
    for line in execution_log.splitlines():
        operation = line.split()[1]  # [0] is the line number, [1] is the opcode
        if operation.startswith("#"):
            continue
        if operation.endswith(":"):
            summary.add_call(operation[:-1])
        else:
            summary.add_opcode(operation)
    return summary
