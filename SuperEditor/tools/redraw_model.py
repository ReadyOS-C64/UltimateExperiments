"""Independent source40 layout, PETSCII and complete document-screen oracle.

No assembler tables, cached renderer rows, or current screen bytes are inputs.
Positions refer to the merged source, including the uncommitted hot window.
"""
from __future__ import annotations
from dataclasses import dataclass

BODY_ROWS = 22
STATUS_ROW = 24


def screen_code(value):
    """Normal mixed-case screen code for every native PETSCII byte."""
    if value < 32 or 128 <= value < 160:
        return 63
    if value < 64:
        return value
    if value < 96:
        return value - 64
    if value < 128:
        return value - 32
    if value == 255:
        return 94
    if 192 <= value < 224:
        return value - 128
    return (value % 32) + 96


def native_text(text):
    """Readable host labels to the dialect's case-preserving PETSCII."""
    return bytes(ord(c) + 128 if 'A' <= c <= 'Z' else
                 ord(c) - 32 if 'a' <= c <= 'z' else ord(c)
                 for c in text)


@dataclass(frozen=True)
class Screen:
    matrix: bytes
    colors: bytes
    anchors: tuple
    caret: tuple | None


def menu_header():
    """Exact source40 menu frame; graphic separators are screen codes."""
    matrix = bytearray([32] * 40 + [0x40] * 40)
    colors = bytearray([1] * 40 + [7] * 40)
    for column, text in [(1, 'File'), (7, 'Edit'), (13, 'View'),
                         (19, 'Navigate'), (28, 'Block'), (35, 'Help')]:
        codes = bytes(map(screen_code, native_text(text)))
        matrix[column:column + len(codes)] = codes
    for column in (0, 6, 12, 18, 27, 34, 39):
        matrix[column], colors[column] = 0x5D, 7
    matrix[40], matrix[79] = 0x6D, 0x7D
    for column in (6, 12, 18, 27, 34):
        matrix[40 + column] = 0x71
    return bytes(matrix), bytes(colors)


def source40(source, top, caret, *, marked=False, anchor=0, pending=False,
             dirty=False, error=0, history_fault=False, trimmed=False):
    """Build all 1000 visible cells for the plain document UI.

    A CR occupies one selectable blank cell and ends its row. A CR immediately
    after a full row consequently occupies the following empty row. EOF rows
    share a source anchor, but only the first EOF cell carries the caret.
    """
    assert 0 <= top <= len(source) and 0 <= caret <= len(source)
    matrix = bytearray([32] * 1000)
    colors = bytearray([1] * 1000)

    def label(text, row, column):
        codes = bytes(map(screen_code, native_text(text)))
        assert column + len(codes) <= 40
        matrix[row * 40 + column:row * 40 + column + len(codes)] = codes

    lo, hi = sorted((anchor, caret)) if marked else (caret, caret)
    pos = top
    anchors = []
    visible_caret = None
    for row in range(BODY_ROWS):
        anchors.append(pos)
        for col in range(40):
            at = (row + 2) * 40 + col
            eof = pos == len(source)
            cr = not eof and source[pos] == 13
            code = 32 if eof or cr else screen_code(source[pos])
            ink = 1
            if marked and lo <= pos < hi:
                code ^= 128
                ink = 3
            if pos == caret and visible_caret is None:
                code = (32 if eof or cr else screen_code(source[pos])) ^ 128
                ink = 7 if marked else 3
                visible_caret = (row, col)
            matrix[at], colors[at] = code, ink
            if eof:
                break
            pos += 1
            if cr:
                break
    anchors.append(pos)
    matrix[:80], colors[:80] = menu_header()
    colors[STATUS_ROW * 40:(STATUS_ROW + 1) * 40] = bytes([15] * 40)
    hint = {0x7C: 'Invalid number/text / F6 Help',
            0x7D: 'No such line / F6 Help',
            0x7E: 'No match / CTRL-N next / F6 Help'}.get(error)
    if hint is None and history_fault:
        hint = 'Undo fault: Edit/C clear / F6 Help'
    if hint is None and not error and trimmed:
        hint = 'Undo full: oldest dropped / F6 Help'
    if hint:
        label(hint, STATUS_ROW, 1)
    elif error:
        label('Error', STATUS_ROW, 1)
        matrix[STATUS_ROW * 40 + 7:STATUS_ROW * 40 + 9] = f'{error:02X}'.encode('ascii')
        label('F6 Help', STATUS_ROW, 32)
    else:
        label('Pos:', STATUS_ROW, 1)
        # Hex glyphs are written directly, so A-F are uppercase screen codes.
        matrix[STATUS_ROW * 40 + 6:STATUS_ROW * 40 + 12] = f'{caret:06X}'.encode('ascii')
        label('Modified' if pending or dirty else 'Clean', STATUS_ROW, 14)
        if marked:
            label('Mark', STATUS_ROW, 23)
        label('F6 Help', STATUS_ROW, 32)
    return Screen(bytes(matrix), bytes(colors), tuple(anchors), visible_caret)


def changed_body_rows(before, after):
    """Rows requiring a visible update, independently of renderer damage state."""
    rows = set()
    for row in range(BODY_ROWS):
        start, end = (row + 2) * 40, (row + 3) * 40
        if (before.matrix[start:end] != after.matrix[start:end] or
                before.colors[start:end] != after.colors[start:end]):
            rows.add(row)
    return rows


def verify_screen(actual_matrix, actual_colors, expected, *, tag='screen'):
    for name, actual, wanted in [('matrix', actual_matrix, expected.matrix),
                                 ('colors', bytes(c & 15 for c in actual_colors),
                                  expected.colors)]:
        if actual != wanted:
            differences = [(i // 40, i % 40, a, b)
                           for i, (a, b) in enumerate(zip(actual, wanted)) if a != b]
            raise AssertionError((tag, name, 'row,col,actual,expected', differences[:16],
                                  'total', len(differences)))
