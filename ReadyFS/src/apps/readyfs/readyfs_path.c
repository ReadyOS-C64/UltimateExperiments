#include "readyfs_path.h"

#include <string.h>

static unsigned char is_digit(char ch) {
    return (unsigned char)(ch >= '0' && ch <= '9');
}

static unsigned char parse_byte(const char *text, unsigned char *pos,
                                unsigned char limit, unsigned char *out) {
    unsigned int value;

    if (!is_digit(text[*pos])) return RF_PATH_BAD_ENDPOINT;
    value = 0u;
    do {
        value = (unsigned int)(value * 10u +
                (unsigned int)(text[*pos] - '0'));
        if (value > limit) return RF_PATH_BAD_DEVICE;
        ++*pos;
    } while (is_digit(text[*pos]));
    *out = (unsigned char)value;
    return RF_PATH_OK;
}

static unsigned char endpoint_path_start(const char *text,
                                         ReadyFsPath *out) {
    unsigned char pos;
    unsigned char rc;

    if (text[0] == 'u' && text[1] == ':') {
        out->endpoint = RF_EP_ULTIMATE;
        out->path_offset = 2u;
        return RF_PATH_OK;
    }
    if (text[0] == 't' && text[1] == ':') {
        out->endpoint = RF_EP_TAPE;
        out->unit = 1u;
        out->path_offset = 2u;
        return RF_PATH_OK;
    }
    if (text[0] == '@') {
        pos = 1u;
        while (text[pos] != 0 && text[pos] != ':' && pos < 17u) {
            ++pos;
        }
        if (pos == 1u || text[pos] != ':') {
            return RF_PATH_BAD_ENDPOINT;
        }
        out->endpoint = RF_EP_ALIAS;
        out->alias_len = (unsigned char)(pos - 1u);
        out->path_offset = (unsigned char)(pos + 1u);
        return RF_PATH_OK;
    }
    if (text[0] == 's' && is_digit(text[1])) {
        pos = 1u;
        rc = parse_byte(text, &pos, 255u, &out->unit);
        if (rc != RF_PATH_OK) return rc;
        if (text[pos] != ':') {
            return RF_PATH_BAD_ENDPOINT;
        }
        out->endpoint = RF_EP_SOFTIEC;
        out->path_offset = (unsigned char)(pos + 1u);
        return RF_PATH_OK;
    }
    if (is_digit(text[0])) {
        pos = 0u;
        rc = parse_byte(text, &pos, 30u, &out->unit);
        if (rc != RF_PATH_OK) return rc;
        if (text[pos] == '.') {
            ++pos;
            rc = parse_byte(text, &pos, 254u, &out->partition);
            if (rc != RF_PATH_OK) return rc;
        }
        if (text[pos] != ':') {
            return RF_PATH_BAD_ENDPOINT;
        }
        if (out->unit < 8u) {
            return RF_PATH_BAD_DEVICE;
        }
        out->endpoint = RF_EP_IEC;
        out->path_offset = (unsigned char)(pos + 1u);
        return RF_PATH_OK;
    }
    return RF_PATH_BAD_ENDPOINT;
}

unsigned char readyfs_path_has_parent_escape(const char *text) {
    unsigned int i;
    unsigned char at_start;

    at_start = 1u;
    for (i = 0u; text[i] != 0; ++i) {
        if (at_start && text[i] == '.' && text[i + 1u] == '.' &&
            (text[i + 2u] == 0 || text[i + 2u] == '/' ||
             text[i + 2u] == '!')) {
            return 1u;
        }
        at_start = (unsigned char)(text[i] == '/' || text[i] == '!');
    }
    return 0u;
}

unsigned char readyfs_path_parse(const char *text, ReadyFsPath *out) {
    unsigned int len;
    unsigned int i;
    unsigned char rc;
    unsigned char prev_boundary;

    if (out == 0 || text == 0 || text[0] == 0) {
        return RF_PATH_EMPTY;
    }
    memset(out, 0, sizeof(*out));
    len = strlen(text);
    if (len > RF_PATH_MAX) {
        return RF_PATH_TOO_LONG;
    }
    rc = endpoint_path_start(text, out);
    if (rc != RF_PATH_OK) {
        return rc;
    }
    out->absolute = (unsigned char)(text[out->path_offset] == '/');
    prev_boundary = 1u;
    for (i = out->path_offset; i < len; ++i) {
        if (text[i] == '!') {
            if (prev_boundary || i + 1u >= len || text[i + 1u] != '/') {
                return RF_PATH_BAD_SEGMENT;
            }
            if (out->image_depth == 255u) {
                return RF_PATH_BAD_SEGMENT;
            }
            ++out->image_depth;
            prev_boundary = 1u;
            ++i;
            continue;
        }
        prev_boundary = (unsigned char)(text[i] == '/');
    }
    return RF_PATH_OK;
}

unsigned char readyfs_path_normalize(const char *text, char *out) {
    ReadyFsPath parsed;
    unsigned char rc;
    unsigned int read_pos;
    unsigned int write_pos;
    unsigned int floor;
    unsigned int segment_start;
    unsigned int segment_len;
    unsigned char image_boundary;

    if (text == 0 || out == 0) return RF_PATH_EMPTY;
    rc = readyfs_path_parse(text, &parsed);
    if (rc != RF_PATH_OK) return rc;
    if (!parsed.absolute) {
        if (out != text) strcpy(out, text);
        return RF_PATH_OK;
    }
    for (write_pos = 0u; write_pos < parsed.path_offset; ++write_pos) {
        out[write_pos] = text[write_pos];
    }
    out[write_pos++] = '/';
    floor = write_pos;
    read_pos = (unsigned int)parsed.path_offset + 1u;
    while (text[read_pos] != 0) {
        while (text[read_pos] == '/') ++read_pos;
        if (text[read_pos] == 0) break;
        segment_start = read_pos;
        while (text[read_pos] != 0 && text[read_pos] != '/' &&
               text[read_pos] != '!') ++read_pos;
        segment_len = read_pos - segment_start;
        image_boundary = (unsigned char)(text[read_pos] == '!');
        if (!image_boundary && segment_len == 1u &&
            text[segment_start] == '.') {
            /* Current-directory components disappear. */
        } else if (!image_boundary && segment_len == 2u &&
                   text[segment_start] == '.' &&
                   text[segment_start + 1u] == '.') {
            if (write_pos <= floor) return RF_PATH_ESCAPE;
            while (write_pos > floor && out[write_pos - 1u] != '/') {
                --write_pos;
            }
            if (write_pos > floor && out[write_pos - 1u] == '/') --write_pos;
        } else {
            if (write_pos != 0u && out[write_pos - 1u] != '/') {
                if (write_pos >= RF_PATH_MAX) return RF_PATH_TOO_LONG;
                out[write_pos++] = '/';
            }
            if (write_pos + segment_len > RF_PATH_MAX) return RF_PATH_TOO_LONG;
            memmove(out + write_pos, text + segment_start, segment_len);
            write_pos += segment_len;
        }
        if (image_boundary) {
            if (write_pos + 2u > RF_PATH_MAX) return RF_PATH_TOO_LONG;
            out[write_pos++] = '!';
            out[write_pos++] = '/';
            floor = write_pos;
            ++read_pos;
            if (text[read_pos] == '/') ++read_pos;
        }
    }
    if (write_pos > floor && out[write_pos - 1u] == '/') --write_pos;
    out[write_pos] = 0;
    return readyfs_path_parse(out, &parsed);
}

const char *readyfs_path_error(unsigned char rc) {
    switch (rc) {
        case RF_PATH_OK: return "ok";
        case RF_PATH_EMPTY: return "empty path";
        case RF_PATH_TOO_LONG: return "path over 255 bytes";
        case RF_PATH_BAD_ENDPOINT: return "bad endpoint";
        case RF_PATH_BAD_DEVICE: return "bad device";
        case RF_PATH_BAD_SEGMENT: return "bad image boundary";
        case RF_PATH_ESCAPE: return "path escapes protected root";
    }
    return "path error";
}
