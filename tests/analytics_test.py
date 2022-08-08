from io import StringIO

from pyteal import Addr, Assert, Btoi, Bytes, BytesAdd, If, Int, Itob, Pop, Return, ScratchVar, Seq, Txn

from pytealext.evaluator import compile_and_run, summarize_execution


def test_summarize_execution():
    sv = ScratchVar()

    expr = Seq(
        sv.store(Int(1)),  # 2 ops
        sv.store(sv.load() + sv.load()),  # 4 ops
        Pop(Btoi(Itob(sv.load()))),  # 4 ops
        If(sv.load())
        .Then(  # 2 ops (branch + load)
            sv.store(BytesAdd(Itob(Int(1)), Itob(Int(2))))  # 15 ops = (2 x itob, 2 x int, b+, store)
        )
        .Else(Assert(Txn.application_id())),  # unreachable
        Pop(Addr("7777777777777777777777777777777777777777777777777774MSJUVU")),  # 2 ops
        Return(Btoi(Bytes("uuu"))),  # 3 ops
    )
    s = StringIO()

    compile_and_run(expr, debug=s)
    expected_cost = 2 + 4 + 4 + 2 + 15 + 2 + 3
    expected_opcodes = {
        "load": 4,
        "store": 3,
        "int": 3,
        "itob": 3,
        "btoi": 2,
        "pop": 2,
        "return": 1,
        "+": 1,
        "b+": 1,
        "addr": 1,
        "byte": 1,
        "bnz": 1,  # code could as well be compiled using bz, so stability is not guaranteed
    }
    summary = summarize_execution(s.getvalue())

    assert len(summary.call_count) == 2  # the branch + return from branch
    assert summary.execution_cost == expected_cost
    assert summary.opcode_usage == expected_opcodes
