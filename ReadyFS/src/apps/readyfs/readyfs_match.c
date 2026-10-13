#include "readyfs_match.h"
#include "readyfs_path.h"

#include <string.h>
#ifdef __CC65__
#include <conio.h>
#endif

#define RF_MATCH_MAX 255u

static unsigned char match_prev[RF_MATCH_MAX + 1u];
#ifndef READYFS_MONOLITHIC
static char ultimate_name[RF_MATCH_MAX + 1u];
#endif

static unsigned char fold(unsigned char ch) {
    /* Do not use target character literals here.  cc65 translates 'A' to
     * PETSCII $C1, while keyboard-buffer commands and UltimateDOS host names
     * can independently contain ASCII $41-$5A or $61-$7A.  Fold all three
     * spellings to ASCII lowercase so a typed INSIDE matches host `inside`. */
    if (ch >= 0x41u && ch <= 0x5Au) ch = (unsigned char)(ch + 0x20u);
    else if (ch >= 0xC1u && ch <= 0xDAu)
        ch = (unsigned char)(ch - 0x60u);
    return ch;
}

#ifndef READYFS_MONOLITHIC
#ifdef __CC65__
extern void __fastcall__ readyfs_match_decode_name(char *text);
extern void __fastcall__ readyfs_match_strip_type(char *text);
extern void __fastcall__ readyfs_match_strip_annotation(char *text);

/* Keep the physical target on the compact, already proven assembly
 * conversion path.  The host build below remains deliberately defensive so
 * malformed synthetic inputs can still be exercised by unit tests. */
void readyfs_match_normalize_ultimate(char *relative_stem,
                                      unsigned char file) {
    readyfs_match_decode_name(relative_stem);
    if (file) readyfs_match_strip_type(relative_stem);
}

static void readyfs_match_decode_host(char *text) {
    readyfs_match_decode_name(text);
    readyfs_match_strip_annotation(text);
}
#else
static unsigned char hex_value(unsigned char value) {
    if (value >= '0' && value <= '9') return (unsigned char)(value - '0');
    value = fold(value);
    if (value >= 'a' && value <= 'f')
        return (unsigned char)(value - 'a' + 10u);
    return 0xFFu;
}

static unsigned char type_suffix(const char *start, const char *end) {
    unsigned char a;
    unsigned char b;
    unsigned char c;
    if ((unsigned int)(end - start) < 4u || end[-4] != '.') return 0u;
    a = fold((unsigned char)end[-3]);
    b = fold((unsigned char)end[-2]);
    c = fold((unsigned char)end[-1]);
    if (a == 's' && b == 'e' && c == 'q') return 1u;
    if (a == 'p' && b == 'r' && c == 'g') return 2u;
    if (a == 'u' && b == 's' && c == 'r') return 3u;
    if (a == 'r' && b == 'e' && c == 'l') return 4u;
    return 0u;
}

/* UltimateDOS READ_DIR exposes unsafe/lowercase host bytes as bracketed hex
 * and appends a C64 type annotation. Filters are a user-facing contract, so
 * normalize that access spelling in place before matching. The resident tree
 * adapter reconstructs the untouched raw stem before queueing it for I/O. */
void readyfs_match_normalize_ultimate(char *relative_stem,
                                      unsigned char file) {
    char *read;
    char *write;
    char *close;
    char *scan;
    char *component;
    char *end;
    unsigned char high;
    unsigned char low;
    unsigned char type;

    read = write = relative_stem;
    while (*read != 0) {
        if (*read == '[') {
            close = strchr(read + 1, ']');
            if (close != 0 && ((unsigned int)(close - read) & 1u) != 0u) {
                scan = read + 1;
                while (scan < close) {
                    high = hex_value((unsigned char)scan[0]);
                    low = hex_value((unsigned char)scan[1]);
                    if (high == 0xFFu || low == 0xFFu) break;
                    *write++ = (char)((high << 4u) | low);
                    scan += 2;
                }
                if (scan == close) { read = close + 1; continue; }
            }
        }
        *write++ = *read++;
    }
    *write = 0;
    if (!file) return;
    component = strrchr(relative_stem, '/');
    component = component == 0 ? relative_stem : component + 1;
    end = component + strlen(component);
    type = type_suffix(component, end);
    if (type == 0u) return;
    end[-4] = 0;
    end -= 4;
    if (type_suffix(component, end) == type) end[-4] = 0;
}

static void readyfs_match_decode_host(char *text) {
    char *component;
    char *end;
    readyfs_match_normalize_ultimate(text, 0u);
    component = strrchr(text, '/');
    component = component == 0 ? text : component + 1;
    end = component + strlen(component);
    if (type_suffix(component, end) != 0u) end[-4] = 0;
}
#endif
#endif

static unsigned char same_folded(const char *left, const char *right) {
    while (*left != 0 && *right != 0) {
        if (fold((unsigned char)*left++) != fold((unsigned char)*right++))
            return 0u;
    }
    return (unsigned char)(*left == 0 && *right == 0);
}

static unsigned char is_boundary(unsigned char ch) {
    return (unsigned char)(ch == '/' || ch == '!');
}

#ifndef READYFS_MONOLITHIC
static void resolve_path_call(ReadyFsResolveCall *call) {
    ReadyFsPath parsed;
    const char *suffix;
    const char *colon;
    unsigned int root_len;
    unsigned int suffix_len;
    unsigned char rc;

    if (call == 0 || call->input == 0 || call->input[0] == 0 ||
        call->cwd == 0 || call->output == 0) {
        if (call != 0) call->result = RF_PATH_EMPTY;
        return;
    }
    rc = readyfs_path_parse(call->input, &parsed);
    if (rc == RF_PATH_OK && parsed.endpoint != RF_EP_ALIAS) {
        strcpy(call->output, call->input);
        call->result = readyfs_path_normalize(call->output, call->output);
        return;
    }
    if (rc == RF_PATH_OK && parsed.endpoint == RF_EP_ALIAS) {
        if (call->alias_root == 0) {
            call->result = RF_PATH_BAD_ENDPOINT;
            return;
        }
        suffix = call->input + parsed.path_offset;
        if (readyfs_path_has_parent_escape(suffix)) {
            call->result = RF_PATH_ESCAPE;
            return;
        }
        root_len = strlen(call->alias_root);
        suffix_len = strlen(suffix);
        if (root_len + suffix_len + 1u > RF_PATH_MAX) {
            call->result = RF_PATH_TOO_LONG;
            return;
        }
        strcpy(call->output, call->alias_root);
        if (root_len != 0u && call->output[root_len - 1u] == '/' &&
            suffix[0] == '/') {
            ++suffix;
        } else if (root_len != 0u && call->output[root_len - 1u] != '/' &&
                   suffix[0] != '/' && suffix[0] != 0) {
            call->output[root_len++] = '/';
            call->output[root_len] = 0;
        }
        strcat(call->output, suffix);
    } else {
        if (strchr(call->input, ':') != 0) {
            call->result = rc;
            return;
        }
        if (call->input[0] == '/') {
            colon = strchr(call->cwd, ':');
            if (colon == 0) {
                call->result = RF_PATH_BAD_ENDPOINT;
                return;
            }
            root_len = (unsigned int)(colon - call->cwd + 1u);
            if (root_len + strlen(call->input) > RF_PATH_MAX) {
                call->result = RF_PATH_TOO_LONG;
                return;
            }
            memcpy(call->output, call->cwd, root_len);
            strcpy(call->output + root_len, call->input);
        } else {
            root_len = strlen(call->cwd);
            suffix_len = strlen(call->input);
            if (root_len + suffix_len + 2u > RF_PATH_MAX) {
                call->result = RF_PATH_TOO_LONG;
                return;
            }
            strcpy(call->output, call->cwd);
            if (root_len != 0u && call->output[root_len - 1u] != '/') {
                call->output[root_len++] = '/';
                call->output[root_len] = 0;
            }
            strcat(call->output, call->input);
        }
    }
    rc = readyfs_path_parse(call->output, &parsed);
    if (rc == RF_PATH_OK)
        rc = readyfs_path_normalize(call->output, call->output);
    call->result = rc;
}
#endif

unsigned char readyfs_match(const char *pattern, const char *relative_stem) {
    unsigned int pattern_len;
    unsigned int stem_len;
    unsigned int pi;
    unsigned int si;
    unsigned char can_start;
    unsigned char globstar;
    unsigned char original_left;
    unsigned char original_self;

#ifndef READYFS_MONOLITHIC
    if (pattern == RF_MATCH_RESOLVE_PATH) {
        resolve_path_call((ReadyFsResolveCall *)relative_stem);
        return 1u;
    }
#endif

#ifndef READYFS_MONOLITHIC
    if (pattern == RF_MATCH_ULTIMATE_FIND) {
        ReadyFsUltimateFindCall *call;
        if (relative_stem == 0) return 0u;
        call = (ReadyFsUltimateFindCall *)relative_stem;
        if (call->wanted == 0 || call->entry == 0 || call->access == 0 ||
            call->entry_length == 0u || call->entry_length > RF_MATCH_MAX)
            return 0u;
        memcpy(ultimate_name, call->entry, call->entry_length);
        ultimate_name[call->entry_length] = 0;
        /* Accept the actual host spelling as well as the decoded logical name.
         * A literal .SEQ filename must remain findable for delete/replace. */
        if (!same_folded(call->wanted, ultimate_name)) {
            readyfs_match_decode_host(ultimate_name);
            if (!same_folded(call->wanted, ultimate_name)) return 0u;
        }
        memcpy(call->access, call->entry, call->entry_length);
        call->access[call->entry_length] = 0;
#ifdef __CC65__
        if (call->display != 0) {
            cputs("display: "); cputs(call->display); cputc('\r'); cputc('\n');
            cputs("access: "); cputs(call->access); cputc('\r'); cputc('\n');
            cputs("host: "); cputs(ultimate_name); cputc('\r'); cputc('\n');
        }
#endif
        return 1u;
    }
    if (pattern == RF_MATCH_ULTIMATE_FILTER) {
        ReadyFsUltimateMatchCall *call;
        if (relative_stem == 0) return 0u;
        call = (ReadyFsUltimateMatchCall *)relative_stem;
        if (call->stem == 0) return 0u;
        if ((call->file & RF_MATCH_RAW_STEM) == 0u)
            readyfs_match_normalize_ultimate(call->stem, call->file);
        if (call->include != 0 &&
            !readyfs_match(call->include, call->stem)) return 0u;
        if (call->exclude != 0 &&
            readyfs_match(call->exclude, call->stem)) return 0u;
        return 1u;
    }
    if (pattern == RF_MATCH_NORMALIZE_FILE ||
        pattern == RF_MATCH_NORMALIZE_DIR) {
        if (relative_stem == 0) return 0u;
        readyfs_match_normalize_ultimate(
            (char *)relative_stem,
            (unsigned char)(pattern == RF_MATCH_NORMALIZE_FILE));
        return 1u;
    }
#endif
    if (pattern == 0 || relative_stem == 0) return 0u;
    pattern_len = strlen(pattern);
    stem_len = strlen(relative_stem);
    if (pattern_len > RF_MATCH_MAX || stem_len > RF_MATCH_MAX) return 0u;
    memset(match_prev, 0, stem_len + 1u);
    match_prev[0] = 1u;
    pi = 0u;
    while (pi < pattern_len) {
        if (pattern[pi] == '*') {
            globstar = (unsigned char)(pi + 1u < pattern_len &&
                                       pattern[pi + 1u] == '*');
            if (globstar && pi + 2u < pattern_len &&
                pattern[pi + 2u] == '/') {
                /* A recursive-star followed by slash is one token: zero
                 * directories, or any prefix ending on a separator. */
                can_start = 0u;
                original_left = match_prev[0];
                for (si = 1u; si <= stem_len; ++si) {
                    original_self = match_prev[si];
                    if (original_left) can_start = 1u;
                    match_prev[si] = (unsigned char)(original_self ||
                        (can_start && relative_stem[si - 1u] == '/'));
                    original_left = original_self;
                }
                pi += 3u;
            } else {
                for (si = 1u; si <= stem_len; ++si) {
                    match_prev[si] = (unsigned char)(match_prev[si] ||
                        (match_prev[si - 1u] &&
                         (globstar || !is_boundary((unsigned char)
                                                   relative_stem[si - 1u]))));
                }
                pi += globstar ? 2u : 1u;
            }
        } else {
            for (si = stem_len; si != 0u; --si) {
                if (pattern[pi] == '?') {
                    match_prev[si] = (unsigned char)(match_prev[si - 1u] &&
                        !is_boundary((unsigned char)relative_stem[si - 1u]));
                } else match_prev[si] = (unsigned char)(match_prev[si - 1u] &&
                    fold((unsigned char)pattern[pi]) ==
                    fold((unsigned char)relative_stem[si - 1u]));
            }
            match_prev[0] = 0u;
            ++pi;
        }
    }
    return match_prev[stem_len];
}
