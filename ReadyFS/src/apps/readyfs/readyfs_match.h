#ifndef READYFS_MATCH_H
#define READYFS_MATCH_H

/* Shell matching is case-insensitive. '*' and '?' stop at '/' or '!', while
 * '**' crosses directory and image-boundary components. */
unsigned char readyfs_match(const char *pattern, const char *relative_stem);
void readyfs_match_normalize_ultimate(char *relative_stem,
                                      unsigned char file);

#define RF_MATCH_NORMALIZE_FILE ((const char *)1u)
#define RF_MATCH_NORMALIZE_DIR  ((const char *)2u)

typedef struct {
    const char *pattern;
    const char *stem;
} ReadyFsMatchCall;

typedef struct {
    const char *include;
    const char *exclude;
    char *stem;
    unsigned char file;
} ReadyFsUltimateMatchCall;

#define RF_MATCH_ULTIMATE_FILTER ((const char *)3u)
#define RF_MATCH_RAW_STEM 0x80u

typedef struct {
    const char *wanted;
    const unsigned char *entry;
    unsigned int entry_length;
    char *access;
    const char *display;
} ReadyFsUltimateFindCall;

#define RF_MATCH_ULTIMATE_FIND ((const char *)4u)

/* Overlay-1 also owns the pure canonical-path join.  Alias-table lookup stays
 * resident because it is REU I/O; the helper receives the already-resolved
 * alias root, or NULL for an ordinary absolute/relative path. */
typedef struct {
    const char *input;
    const char *cwd;
    const char *alias_root;
    char *output;
    unsigned char result;
} ReadyFsResolveCall;

#define RF_MATCH_RESOLVE_PATH ((const char *)5u)

#endif
