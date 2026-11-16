"""Execute the native keyboard and question console in Peddle with host-preloaded REU."""
import argparse
from pathlib import Path
import struct

from probe.check_local import load_native, seed_pal_clock
from tools.oracle import Network, input_tokens
from tools.peddle import Machine
from tools.run_peddle import STEP_LIMIT

KEY_COLUMNS = ("\b\r......", "3wa4zseS", "5rd6cftx", "7yg8bhuv",
               "9ij0mkon", "+pl-.:@,", ".*;.S=^/", "1..2 .q\x03")


def set_keys(matrix, *positions):
    matrix[:] = [0xff] * 8
    for column, row in positions:
        matrix[column] &= ~(1 << row)


def type_chars(machine, matrix, text):
    carry = 0
    for char in text:
        key = next((col, keys.index(char.lower())) for col, keys in enumerate(KEY_COLUMNS)
                   if char.lower() in keys and char != ".") if char != "." else (5, 4)
        keys = (key, (1, 7)) if char.isupper() else (key,)
        set_keys(matrix, *keys)
        machine.run("keyboard_input")
        assert not machine.accumulator
        machine.run("keyboard_input")
        assert machine.accumulator == ord(char), (char, machine.accumulator)
        carry = machine.run("console_edit", machine.accumulator)[4] & 1
        machine.run("keyboard_input")
        assert not machine.accumulator
        set_keys(matrix)
        machine.run("keyboard_input")
        machine.run("keyboard_input")
        assert not machine.accumulator
    return carry


def screen(machine, row, count=39):
    address = 0x400 + 40 * row + 1
    return "".join(chr(code + 96 if 1 <= code <= 26 else code)
                   for code in machine.ram[address:address + count])


def check(bundle, checkpoint):
    machine = Machine()
    try:
        load_native(machine, bundle)
        machine.preload((bundle / "MODEL.BIN").read_bytes())
        machine.put("reu_banks", 32)
        assert not machine.run("model_open")[4] & 1
        matrix = machine.keyboard_matrix()
        machine.run("console_prepare")
        seed_pal_clock(machine)
        assert not type_chars(machine, matrix, "  \r")
        assert machine.get("token_pos", 1) == 0
        assert not type_chars(machine, matrix, "\x03")

        edited = "WHAT IS 7 TIMES 8"
        assert type_chars(machine, matrix, edited + "1\b  \r")
        assert screen(machine, 7).startswith(edited + "  ")
        reference = Network(checkpoint)
        prompt = input_tokens(edited)
        for position, token in enumerate(prompt):
            status = machine.run("question_step", instruction_limit=STEP_LIMIT)[4]
            assert status & 1 == 0 and machine.accumulator == 1
            assert machine.get("token_pos", 1) == position + 1
            reference.step(token, logits=False)
        next_token = 1
        answer = []
        while True:
            status = machine.run("question_step", instruction_limit=STEP_LIMIT)[4]
            assert status & 1 == 0
            expected = tuple(reference.step(next_token, logits=True))
            actual = struct.unpack_from("<97i", machine.ram, machine.symbols["logits"])
            assert expected == actual
            event = machine.accumulator
            if event == 3:
                break
            assert event == 2
            char = machine.get("question_char", 1)
            answer.append(chr(char))
            next_token = char - 30
        assert "".join(answer) == "7 times 8 is 56."
        print("Matrix input, uppercase normalization, deletion, trailing-space trim, and every decode logit passed.",
              flush=True)

        type_chars(machine, matrix, "\x03")
        assert type_chars(machine, matrix, "what is the capital of peru\r")
        for _ in range(2):
            assert not machine.run("question_step", instruction_limit=STEP_LIMIT)[4] & 1
        set_keys(matrix, (7, 7))
        stats = machine.run("run_answer")
        assert stats[2:4] == (0, 0), stats
        assert screen(machine, 10).startswith("Cancelled. Ready.")
        assert machine.get("token_pos", 1) == 0
        assert machine.run("model_choose")[4] & 1
        set_keys(matrix)
        assert type_chars(machine, matrix, "\r")
        machine.run("run_answer", instruction_limit=1_500_000_000)
        assert screen(machine, 12).startswith("Lima."), (screen(machine, 12), screen(machine, 10))
        assert screen(machine, 17).startswith("Elapsed 000.000S"), screen(machine, 17)
        assert screen(machine, 10).startswith("Answer complete."), screen(machine, 10)
        model = (bundle / "MODEL.BIN").read_bytes()
        assert bytes(machine.reu[:len(model)]) == model
        print("RUN/STOP cancelled the partial question, then native screen output resumed with Lima. on the same image.",
              flush=True)

        machine.put("question_length", 0)
        for _ in range(72):
            assert not machine.run("question_append", ord("a"))[4] & 1
        assert machine.run("question_append", ord("z"))[4] & 1
        assert machine.get("question_length", 1) == 72
    finally:
        machine.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--checkpoint", type=Path, default=Path("reference/TINY.BIN"))
    args = parser.parse_args()
    check(args.bundle, args.checkpoint.read_bytes())
