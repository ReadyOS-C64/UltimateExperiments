#ifndef D64_CONFIG_VALIDATE_ONLY
#define D64_CONFIG_VALIDATE_ONLY 0
#endif
#ifndef D64_VALIDATOR_FAST_CRC
#define D64_VALIDATOR_FAST_CRC 0
#endif
#if D64_VALIDATOR_FAST_CRC
#include "validator_crc.h"
#endif
#include "install_config.h"
#include <string.h>

unsigned char d64_cfg_input[D64_CFG_BYTES];
unsigned char d64_cfg_output[D64_CFG_BYTES];
unsigned char d64_path_source[D64_PATH_BYTES];
unsigned char d64_path_relative[D64_PATH_BYTES];
unsigned char d64_path_output[D64_PATH_BYTES];
unsigned char d64_cfg_error;
#if !D64_CONFIG_VALIDATE_ONLY
static unsigned char prepared[D64_CFG_BYTES];
#endif
static unsigned char joined[D64_PATH_BYTES];

#if D64_START_OPTIONS
#pragma code-name ("PRELAUNCH")
#endif
#if D64_VALIDATOR_FAST_CRC
static unsigned long crc32(const unsigned char *p,unsigned int n) {
    return d64_fast_crc(p,n);
}
#else
static unsigned long crc32(const unsigned char *p, unsigned int n) {
    unsigned long crc = 0xffffffffUL;
    unsigned char bit;
    while (n--) {
        crc ^= *p++;
        for (bit = 0; bit < 8u; ++bit)
            crc = (crc >> 1) ^ ((crc & 1u) ? 0xedb88320UL : 0UL);
    }
    return crc ^ 0xffffffffUL;
}

#endif

#if D64_START_OPTIONS
#pragma code-name ("CODE")
#endif
static unsigned char fail(unsigned char error) {
    d64_cfg_error = error;
    return 0u;
}

static unsigned char path_length(const unsigned char *p) {
    unsigned char i;
    for (i = 0; i < D64_PATH_BYTES; ++i)
        if (!p[i]) return i;
    return 0xffu;
}

/* Canonical exact host ASCII, not PETSCII and not a DOS guest pathname. */
static unsigned char path_valid(const unsigned char *p, unsigned char absolute) {
    unsigned char n = path_length(p), i, start;
    if (!n || n == 0xffu || (absolute && p[0] != 0x2fu) ||
        (!absolute && p[0] == 0x2fu)) return 0u;
    if (absolute && n == 1u) return 1u;
    start = absolute ? 1u : 0u;
    for (i = start; i <= n; ++i) {
        if (i != n && p[i] != 0x2fu) {
            if (p[i] < 0x20u || p[i] > 0x7eu || p[i] == 0x5cu ||
                p[i] == 0x3au || p[i] == 0x22u || p[i] == 0x2au ||
                p[i] == 0x3cu || p[i] == 0x3eu || p[i] == 0x3fu ||
                p[i] == 0x7cu) return 0u;
        } else {
            /* FatFs strips trailing spaces/dots; reject those aliases instead
               of validating one spelling and opening a different spelling. */
            if (i == start || p[i-1u] == 0x20u || p[i-1u] == 0x2eu ||
                (i - start == 1u && p[start] == 0x2eu) ||
                (i - start == 2u && p[start] == 0x2eu && p[start+1u] == 0x2eu))
                return 0u;
            start = i + 1u;
        }
    }
    return 1u;
}

#if D64_START_OPTIONS
#pragma code-name ("PRELAUNCH")
#endif
static unsigned char field_valid(const unsigned char *p, unsigned char present) {
    unsigned int i;
    unsigned char n = path_length(p);
    if (!present) {
        for (i = 0; i < D64_PATH_BYTES; ++i) if (p[i]) return 0u;
        return 1u;
    }
    if (!path_valid(p, 1u)) return 0u;
    /* Canonical padding catches hidden bytes after a terminator. */
    for (i = (unsigned int)n + 1u; i < D64_PATH_BYTES; ++i)
        if (p[i]) return 0u;
    return 1u;
}

static unsigned char fields_valid(const unsigned char *p) {
    unsigned char present = p[D64_CFG_PRESENT], ro = p[D64_CFG_READONLY];
    unsigned int i;
    if (!(present & 1u) || (present & 0xf8u) || (ro & 0xf8u) || (ro & ~present))
        return fail(4u);
    if (!field_valid(p+D64_CFG_HOME, 1u) || !field_valid(p+D64_CFG_A, 1u) ||
        !field_valid(p+D64_CFG_B, present & 2u) ||
        !field_valid(p+D64_CFG_C, present & 4u)) return fail(3u);
    if (path_length(p+D64_CFG_A) < 2u ||
        ((present & 2u) && path_length(p+D64_CFG_B) < 2u) ||
        ((present & 4u) && path_length(p+D64_CFG_C) < 2u)) return fail(3u);
    if (p[D64_CFG_PROFILE] || p[D64_CFG_PROFILE+1u] ||
        p[D64_CFG_PROFILE+2u] > 1u || p[D64_CFG_PROFILE+3u] ||
        (!(present & 4u) && p[D64_CFG_PROFILE+2u])) return fail(5u);
    if (!(present & 2u))
        for (i = D64_CFG_B_CRC; i < D64_CFG_B_CRC+4u; ++i)
            if (p[i]) return fail(4u);
    if (p[D64_CFG_BOOT_ABI] != 1u || p[D64_CFG_BOOT_ABI+1u]) return fail(1u);
    /* Explicit configured capacity: 4..16 MiB, in 64 KiB banks. This is not
       hardware detection. DMA callers must still check every owned range. */
    if (p[D64_CFG_REU_BYTES] || p[D64_CFG_REU_BYTES+1u] ||
        p[D64_CFG_REU_BYTES+3u] > 1u ||
        (p[D64_CFG_REU_BYTES+3u] && p[D64_CFG_REU_BYTES+2u]) ||
        (!p[D64_CFG_REU_BYTES+3u] && p[D64_CFG_REU_BYTES+2u] < 0x40u))
        return fail(6u);
    return 1u;
}

#if !D64_CONFIG_VALIDATE_ONLY
unsigned char d64_config_make(void) {
    unsigned long crc;
    unsigned char i;
    d64_cfg_error = 0u;
    if (!fields_valid(d64_cfg_input)) return 0u;
    memset(prepared, 0, sizeof(prepared));
    prepared[0] = 0x44u; prepared[1] = 0x36u;
    prepared[2] = 0x34u; prepared[3] = 0x43u;
    prepared[4] = D64_CFG_VERSION;
    prepared[5] = (unsigned char)D64_CFG_BYTES;
    prepared[6] = (unsigned char)(D64_CFG_BYTES >> 8);
    memcpy(prepared+D64_CFG_HOME, d64_cfg_input+D64_CFG_HOME,
           D64_CFG_REU_BYTES+4u-D64_CFG_HOME);
    /* Reserved bytes cannot smuggle unvalidated settings into a record. */
    prepared[526] = prepared[527] = 0u;
    crc = crc32(prepared, D64_CFG_CRC);
#if D64_VALIDATOR_FAST_CRC
    if(c32_error)return fail(2u);
#endif
    for (i = 0; i < 4u; ++i) {
        prepared[D64_CFG_CRC+i] = (unsigned char)crc;
        crc >>= 8;
    }
    memcpy(d64_cfg_output, prepared, sizeof(prepared));
    return 1u;
}

#endif

unsigned char d64_config_validate(void) {
    unsigned long crc;
    unsigned int i;
    d64_cfg_error = 0u;
    if (d64_cfg_input[0] != 0x44u || d64_cfg_input[1] != 0x36u ||
        d64_cfg_input[2] != 0x34u || d64_cfg_input[3] != 0x43u ||
        d64_cfg_input[4] != D64_CFG_VERSION ||
        d64_cfg_input[5] != (unsigned char)D64_CFG_BYTES ||
        d64_cfg_input[6] != (unsigned char)(D64_CFG_BYTES >> 8) ||
        d64_cfg_input[7] || d64_cfg_input[526] || d64_cfg_input[527])
        return fail(1u);
    for (i = D64_CFG_REU_BYTES+4u; i < D64_CFG_CRC; ++i)
        if (d64_cfg_input[i]) return fail(1u);
    crc = crc32(d64_cfg_input, D64_CFG_CRC);
#if D64_VALIDATOR_FAST_CRC
    if(c32_error)return fail(2u);
#endif
    for (i = 0; i < 4u; ++i) {
        if (d64_cfg_input[D64_CFG_CRC+i] != (unsigned char)crc) return fail(2u);
        crc >>= 8;
    }
    if (!fields_valid(d64_cfg_input)) return 0u;
    memcpy(d64_cfg_output, d64_cfg_input, D64_CFG_BYTES);
    return 1u;
}

#if D64_START_OPTIONS
#pragma code-name ("CODE")
#endif
unsigned char d64_path_join(void) {
    unsigned char home, relative, slash;
    d64_cfg_error = 0u;
    if (!path_valid(d64_path_source, 1u) || !path_valid(d64_path_relative, 0u))
        return fail(3u);
    home = path_length(d64_path_source);
    relative = path_length(d64_path_relative);
    slash = home == 1u ? 0u : 1u;
    if ((unsigned int)home + relative + slash >= D64_PATH_BYTES) return fail(3u);
    memset(joined, 0, sizeof(joined));
    memcpy(joined, d64_path_source, home);
    if (slash) joined[home++] = 0x2fu;
    memcpy(joined+home, d64_path_relative, relative);
    memcpy(d64_path_output, joined, sizeof(joined));
    return 1u;
}

unsigned char d64_path_parent(void) {
    unsigned char n;
    d64_cfg_error = 0u;
    if (!path_valid(d64_path_source, 1u)) return fail(3u);
    n = path_length(d64_path_source);
    memset(joined, 0, sizeof(joined));
    memcpy(joined, d64_path_source, n);
    if (n > 1u) {
        while (n > 1u && joined[n-1u] != 0x2fu) --n;
        if (n > 1u) --n;
        memset(joined+n, 0, D64_PATH_BYTES-n);
    }
    memcpy(d64_path_output, joined, sizeof(joined));
    return 1u;
}
