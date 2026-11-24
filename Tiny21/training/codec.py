"""C64PROGINFO uses Tiny21's byte vocabulary with a real line-break token."""

NEWLINE = 0
END = 1
VOCAB = 97
CONTEXT = 224


def prompt_tokens(text):
    if not text or any(not ' ' <= c <= '~' for c in text):
        raise ValueError(f'invalid ASCII prompt {text!r}')
    return [ord(c) - 30 for c in text.lower()] + [END]


def answer_tokens(text):
    if not text or any(not (' ' <= c <= '~' or c == '\n') for c in text):
        raise ValueError(f'invalid ASCII answer {text!r}')
    return [NEWLINE if c == '\n' else ord(c) - 30 for c in text] + [END]


def display(ids):
    out = []
    for item in ids:
        if item == END:
            break
        out.append('\n' if item == NEWLINE else chr(item + 30))
    return ''.join(out)
