#include "readyfs_ui.h"
#include "readyfs_console.h"
#include "readyfs_reu.h"
#include "readyfs_commands.h"
#include <conio.h>
#include <string.h>

#define UI_ROW 20u
#define UI_ROWS 4u
#define UI_WIDTH 36u
#define UI_END 147u
#define UI_SHIFT_ENTER 141u
#ifdef READYFS_UI_HOST_TEST
extern unsigned char readyfs_ui_test_screen[1000], readyfs_ui_test_color[1000];
extern unsigned char readyfs_ui_test_modifier;
#define UI_MODIFIER readyfs_ui_test_modifier
#define UI_SCREEN readyfs_ui_test_screen
#define UI_COLOR readyfs_ui_test_color
#else
#define UI_MODIFIER (*(volatile unsigned char *)0x028Du)
#define UI_SCREEN ((unsigned char *)0x0400u)
#define UI_COLOR ((unsigned char *)0xD800u)
#endif

static unsigned char length, position, first_row, cursor_row;
static unsigned char overwrite, history_age, continuation;
static unsigned int draft_position;
static unsigned char draft_overwrite, draft_continuation;
static unsigned int change_start, change_end;

static void place_cursor(void) {
    gotoxy((unsigned char)(4u + position - cursor_row * UI_WIDTH),
           (unsigned char)(UI_ROW + cursor_row - first_row));
}

/* Paint only changed buffer cells, clipped to the four visible rows.
 * Appending/overwriting one character writes one cell; deleting at the end
 * writes one space. Cursor keys and unchanged history bounds write no cells. */
static void draw_content(const ReadyFsBatchCall *call) {
    unsigned int limit;
    unsigned char col;
    limit = (first_row + UI_ROWS) * UI_WIDTH;
    if (change_end > limit) change_end = limit;
    limit = first_row * UI_WIDTH;
    if (change_start < limit) change_start = limit;
    textcolor(COLOR_CYAN);
    while (change_start < change_end) {
        col = change_start % UI_WIDTH;
        gotoxy((unsigned char)(4u + col),
               (unsigned char)(UI_ROW + change_start / UI_WIDTH - first_row));
        do {
            cputc(change_start < length ? call->buffer[change_start] : ' ');
            ++change_start;
        } while (++col < UI_WIDTH && change_start < change_end);
    }
}

static void draw_status(void) {
    memset(UI_SCREEN + 960u, 32, 40u);
    gotoxy(0u, 24u);
    textcolor(COLOR_GRAY1);
    cputs(continuation ? "return runs; stop cancels" :
                            "up/dn hist  f1/f3 page");
}

static void draw_frame(void) {
    unsigned char row;
    textcolor(COLOR_LIGHTBLUE);
    for (row = 0u; row < UI_ROWS; ++row) {
        gotoxy(0u, (unsigned char)(UI_ROW + row));
        cputs(first_row + row == 0u ?
              (overwrite ? "ov> " : "rf> ") : "..> ");
    }
}

static void show_output(unsigned int end) {
    unsigned int start, index, slot;
    unsigned char row;
    start = end > 23u ? end - 23u : 0u;
    for (index = start, row = 0u; index < end; ++index, ++row) {
        slot = (readyfs_console_head + RF_CONSOLE_ROWS -
                readyfs_console_used + index) % RF_CONSOLE_ROWS;
        (void)readyfs_reu_console_fetch(slot * RF_CONSOLE_ROW_BYTES,
                 (void *)(UI_SCREEN + (unsigned int)row * 40u), 40u);
        (void)readyfs_reu_console_fetch(slot * RF_CONSOLE_ROW_BYTES + 40u,
                 (void *)(UI_COLOR + (unsigned int)row * 40u), 40u);
    }
    if (row < 23u) memset(UI_SCREEN + (unsigned int)row * 40u,
                          32, (23u-row) * 40u);
}

static void output_history(void) {
    unsigned int end, previous;
    unsigned char key;
    if (readyfs_console_used == 0u) return;
    (void)readyfs_reu_batch_store(RF_UI_LIVE_SCREEN_OFF,
                                 (const void *)UI_SCREEN, 1000u);
    (void)readyfs_reu_batch_store(RF_UI_LIVE_COLOR_OFF,
                                 (const void *)UI_COLOR, 1000u);
    end = readyfs_console_used;
    show_output(end);
    memset(UI_SCREEN + 920u, 32, 80u);
    gotoxy(0u,24u);
    textcolor(COLOR_LIGHTBLUE);
    cputs("output: f1 older f3 newer stop live");
    for (;;) {
        key = cgetc();
        previous = end;
        if (key == CH_F1 ||
            (key == CH_CURS_UP && (UI_MODIFIER & 2u))) {
            if (end > 23u) end -= 23u;
        } else if (key == CH_F3 ||
                   (key == CH_CURS_DOWN && (UI_MODIFIER & 2u))) {
            if (end == readyfs_console_used) break;
            end += 23u;
            if (end > readyfs_console_used) end = readyfs_console_used;
        } else if (key == CH_STOP || key == CH_ENTER) break;
        else continue;
        if (end != previous) show_output(end);
    }
    (void)readyfs_reu_batch_fetch(RF_UI_LIVE_SCREEN_OFF,
                                  (void *)UI_SCREEN, 1000u);
    (void)readyfs_reu_batch_fetch(RF_UI_LIVE_COLOR_OFF,
                                  (void *)UI_COLOR, 1000u);
}

static unsigned char needs_continuation(const char *text) {
    unsigned char quote;
    unsigned int i;
    if (length != 0u && text[length-1u] == '\\') return 1u;
    quote = 0u;
    for (i = 0u; i < length; ++i) if (text[i] == '"') quote ^= 1u;
    return quote;
}

unsigned char readyfs_ui_editor(ReadyFsBatchCall *call) {
    unsigned char key, frame, status, row;
    unsigned int i, old_first, old_position;
    if (call == 0 || call->buffer == 0 || call->capacity < 2u) return 0u;
    readyfs_console_recording = 0u;
    length = position = first_row = cursor_row = 0u;
    overwrite = continuation = 0u;
    history_age = 255u;
    call->buffer[0] = 0;
    row = wherey();
    while (row > UI_ROW) { readyfs_console_scroll(); --row; }
    draw_frame();
    change_start = 0u; change_end = 288u;
    draw_content(call); draw_status(); place_cursor();
    for (;;) {
        key = cgetc();
        old_first = first_row;
        old_position = position;
        change_start = change_end = 0u;
        frame = status = 0u;
        if (key == CH_ENTER && !needs_continuation(call->buffer)) {
            break;
        } else if (key == CH_STOP) {
            length = 0u; break;
        } else if (key == CH_ENTER || key == UI_SHIFT_ENTER || key == CH_F7) {
            change_start = length;
            if (length != 0u && call->buffer[length-1u] == '\\') {
                --length; --change_start;
            }
            if (length + 1u < call->capacity) call->buffer[length++] = ' ';
            call->buffer[length] = 0;
            position = length;
            change_end = length;
            status = !continuation; continuation = 1u;
        } else if (key == CH_F1 ||
                   (key == CH_CURS_UP && (UI_MODIFIER & 2u))) {
            output_history();
        } else if (key == CH_CURS_UP) {
            if (readyfs_reu_history_count() != 0u) {
                if (history_age == 255u) {
                    (void)readyfs_reu_batch_store(RF_UI_DRAFT_OFF,
                                                 call->buffer, call->capacity);
                    draft_position = position; draft_overwrite = overwrite;
                    draft_continuation = continuation;
                    history_age = 0u;
                } else {
                    if (history_age + 1u >= readyfs_reu_history_count()) continue;
                    ++history_age;
                }
                (void)readyfs_reu_history_get(history_age, call->buffer);
                length = position = strlen(call->buffer);
                status = continuation; continuation = 0u;
                change_end = 288u;
            }
        } else if (key == CH_CURS_DOWN && !(UI_MODIFIER & 2u) && history_age != 255u) {
            if (history_age != 0u) {
                --history_age;
                (void)readyfs_reu_history_get(history_age, call->buffer);
                length = position = strlen(call->buffer);
                status = continuation; continuation = 0u;
            } else {
                history_age = 255u;
                (void)readyfs_reu_batch_fetch(RF_UI_DRAFT_OFF,
                                             call->buffer, call->capacity);
                length = strlen(call->buffer);
                position = draft_position; overwrite = draft_overwrite;
                frame = 1u;
                status = continuation != draft_continuation;
                continuation = draft_continuation;
            }
            change_end = 288u;
        } else if (key == CH_CURS_LEFT) { if (position) --position; }
        else if (key == CH_CURS_RIGHT) { if (position < length) ++position; }
        else if (key == CH_HOME) position = 0u;
        else if (key == UI_END) position = length;
        else if (key == CH_INS) { overwrite ^= 1u; frame = 1u; }
        else if (key == CH_DEL && position != 0u) {
            --position; --length;
            memmove(call->buffer + position, call->buffer + position + 1u,
                    length - position + 1u);
            change_start = position; change_end = length + 1u;
        } else if (key >= 32u && key != 127u && (key & 0xE0u) != 0x80u) {
            if (overwrite && position < length) {
                call->buffer[position++] = (char)key;
                change_end = position;
            } else if (length + 1u < call->capacity) {
                memmove(call->buffer + position + 1u, call->buffer + position,
                        length - position + 1u);
                call->buffer[position++] = (char)key; ++length;
                change_end = length;
            }
            change_start = old_position;
        }
        cursor_row = position / UI_WIDTH;
        if (cursor_row < first_row) first_row = cursor_row;
        if (cursor_row >= first_row + UI_ROWS)
            first_row = cursor_row - UI_ROWS + 1u;
        if (old_first != first_row) {
            frame = 1u; change_start = 0u; change_end = 288u;
        }
        if (frame) draw_frame();
        if (change_start < change_end) draw_content(call);
        if (status) draw_status();
        place_cursor();
    }
    call->buffer[length] = 0;
    /* Repaint the input area as transcript only once, then output normally. */
    memset(UI_SCREEN + 800u, 32, 200u);
    gotoxy(0u, UI_ROW);
    readyfs_console_recording = 1u;
    textcolor(COLOR_CYAN);
    cputs("rf> ");
    for (i = 0u; i < length; ++i) cputc(call->buffer[i]);
    cputs("\r\n");
    textcolor(COLOR_WHITE);
    return 1u;
}

extern const char readyfs_long_options[];
static const char *const option_short[] = {"-r","-w","-x","-f","-i","-l","-n","-np","-t","-y","-a","-c","-lb","-id","-ds","-nv"};
static const unsigned char option_offsets[] = {0,12,22,32,40,50,57,64,81,88,94,102,113,121,126,139};
extern unsigned char __fastcall__ readyfs_same_word(const char *a, const char *b);
#define word_equal readyfs_same_word
unsigned char readyfs_ui_prepare(ReadyFsTreeCall *call) {
    unsigned char i,j,start;
    const char *word;
    call->result = readyfs_command_id(call->name);
    if (call->command_args == 0 || (call->result & 0x80u)) return 1u;
    start = 2u;
    if (call->result == RF_COMMAND_COPY || call->result == RF_COMMAND_MOVE ||
        call->result == RF_COMMAND_RENAME || call->result == RF_COMMAND_COMPARE ||
        call->result == RF_COMMAND_WRITE || call->result == RF_COMMAND_APPEND)
        start = 3u;
    for (i=start;i<call->command_argc;++i) {
        word = call->command_args[i];
        for (j=0u;j<16u;++j) {
            if (word_equal(word, option_short[j]) ||
                word_equal(word, readyfs_long_options + option_offsets[j])) {
                call->command_args[i] = (char *)readyfs_long_options + option_offsets[j];
                if (j == 2u || j == 4u || j == 6u || j == 8u || j == 12u || j == 13u) ++i;
                break;
            }
        }
    }
    return 1u;
}
