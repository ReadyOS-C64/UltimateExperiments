"""Observe the native CIA1 keyboard and cancellation on a physical console."""
import re
import time

from video_capture import screen_codes

PROMPT = "what is 7 times 8"
ANSWER = "7 times 8 is 56."
SCREEN = 0x0400


def verify(device, frames, out, bundle, marker, timeout, *, color, visible, png, save_json):
    labels = {}
    for line in (bundle / "probe.lbl").read_text().splitlines():
        _, address, label = line.split()
        labels[label] = int(address, 16)
    question = labels[".question_text"]
    question_end = labels[".question_end"]
    deadline = time.monotonic() + timeout
    wanted = ("Cancelled. Ready.", "Answer complete. Ready.")
    evidence = []
    observed_inference = False
    green = 0
    save_json(out / "keyboard-ready.json", {
        "physical_prompt": PROMPT, "expected_answer_after_retry": ANSWER,
        "action": "Type the question, press RETURN, then hold RUN/STOP until cancelled. "
                  "Release RUN/STOP and submit the same question again.",
    })
    while time.monotonic() < deadline:
        try:
            frame = frames.receive(min(deadline, time.monotonic() + 10))
        except TimeoutError:
            continue
        if not visible(frame, marker):
            raise RuntimeError("native console marker disappeared during keyboard check")
        phase = color(frame)
        if phase in (3, 4):
            if not observed_inference:
                png(frame, out / f"manual-inference-{len(evidence) + 1}.png")
            observed_inference = True
        green = green + 1 if phase == 5 else 0
        if not observed_inference or green < 3:
            continue
        observed_inference = False
        status = device.capture_memory(SCREEN + 40 * 10, 40).strip(b" ")
        if status != screen_codes(wanted[len(evidence)]):
            continue
        # RETURN retains the submitted bytes. They remain available after
        # run_answer resets the editor length and repaints the empty prompt.
        length, = device.capture_memory(question_end, 1)
        if length != len(PROMPT):
            continue
        submitted = device.capture_memory(question, length).decode("ascii")
        if submitted.lower() != PROMPT:
            continue
        finished = len(evidence) == 1
        if finished:
            result = device.capture_memory(SCREEN + 40 * 12 + 1, 79).rstrip(b" ")
            if result != screen_codes(ANSWER):
                raise RuntimeError(f"native keyboard retry produced {result.hex()}")
        timing = device.capture_memory(SCREEN + 40 * 17, 40).lstrip(b" ")
        match = re.match(screen_codes("Elapsed ") + rb"(\d{3}\.\d{3})", timing)
        if not match:
            raise RuntimeError("native keyboard check did not publish elapsed time")
        stage = "restart" if finished else "cancel"
        png(frame, out / f"manual-{stage}.png")
        evidence.append(dict(stage=stage, submitted=submitted,
                             status=wanted[len(evidence)],
                             elapsed_seconds=float(match[1]),
                             answer=ANSWER if finished else None))
        save_json(out / "physical-keyboard.json", evidence)
        print(f"physical keyboard verified {stage}", flush=True)
        if finished:
            return evidence
    raise TimeoutError("physical keyboard qualification incomplete")
