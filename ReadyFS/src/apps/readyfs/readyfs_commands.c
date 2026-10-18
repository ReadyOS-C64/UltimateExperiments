#include "readyfs_commands.h"

#ifdef __CC65__
extern unsigned char __fastcall__ readyfs_same_word(const char *a, const char *b);
#define same_word readyfs_same_word
#else
static unsigned char same_word(const char *left, const char *right) {
    unsigned char a;
    unsigned char b;
    while (*left != 0 && *right != 0) {
        a = (unsigned char)*left++;
        b = (unsigned char)*right++;
        if (a >= 'A' && a <= 'Z') a = (unsigned char)(a + 32u);
        if (b >= 'A' && b <= 'Z') b = (unsigned char)(b + 32u);
        if (a != b) return 0u;
    }
    return (unsigned char)(*left == 0 && *right == 0);
}

#endif

/* The monolithic lab links this normally. The overlay build links the same
 * object into slot 13, so the resident sees only numeric command IDs. */
static const unsigned char command_names[] = {
    RF_COMMAND_EXIT, 'q',0,
    RF_COMMAND_HELP, 'h',0,
    RF_COMMAND_PROBE, 'p','b',0,
    RF_COMMAND_PROFILE, 'p','f',0,
    RF_COMMAND_NATIVE, 'n','t',0,
    RF_COMMAND_DRIVES, 'd','v',0,
    RF_COMMAND_PWD, 'p','w',0,
    RF_COMMAND_HISTORY, 'h','i',0,
    RF_COMMAND_CLEAR, 'c','l',0,
    RF_COMMAND_ALIAS, 'a','l',0,
    RF_COMMAND_UNALIAS, 'u','a',0,
    RF_COMMAND_CONFIG, 'c','f',0,
    RF_COMMAND_DIR, 'd',0,
    RF_COMMAND_TREE, 't','r',0,
    RF_COMMAND_STAT, 's','t',0,
    RF_COMMAND_VOLUME, 'v','l',0,
    RF_COMMAND_MATCH, 'm','t',0,
    RF_COMMAND_TYPE, 't','y',0,
    RF_COMMAND_RENAME, 'r','n',0,
    RF_COMMAND_DELETE, 'd','l',0,
    RF_COMMAND_COMPARE, 'c','m',0,
    RF_COMMAND_NEW, 'n','w',0,
    RF_COMMAND_WRITE, 'w','r',0,
    RF_COMMAND_APPEND, 'a','p',0,
    RF_COMMAND_MOUNT, 'm','o',0,
    RF_COMMAND_DISMOUNT, 'u','m',0,
    RF_COMMAND_SWAP, 's','w',0,
    RF_COMMAND_CAPABILITIES, 'c','a',0,
    RF_COMMAND_STATUS, 's','s',0,
    RF_COMMAND_FIND, 'f','i',0,
    RF_COMMAND_HEAD, 'h','d',0,
    RF_COMMAND_TAIL, 't','l',0,
    RF_COMMAND_CRC32, 'c','r',0,
    RF_COMMAND_TEST, 't','s',0,
    RF_COMMAND_RUN, 'r','u',0,
    RF_COMMAND_MOUNT, 'f','m',0,

    RF_COMMAND_EXIT, 'e','x','i','t',0,
    RF_COMMAND_EXIT, 'q','u','i','t',0,
    RF_COMMAND_HELP, 'h','e','l','p',0,
    RF_COMMAND_PROBE, 'p','r','o','b','e',0,
    RF_COMMAND_PROFILE, 'p','r','o','f','i','l','e',0,
    RF_COMMAND_NATIVE, 'n','a','t','i','v','e',0,
    RF_COMMAND_DRIVES, 'd','r','i','v','e','s',0,
    RF_COMMAND_PWD, 'p','w','d',0,
    RF_COMMAND_HISTORY, 'h','i','s','t','o','r','y',0,
    RF_COMMAND_CLEAR, 'c','l','e','a','r',0,
    RF_COMMAND_CLEAR, 'c','l','s',0,
    RF_COMMAND_CD, 'c','d',0,
    RF_COMMAND_ALIAS, 'a','l','i','a','s',0,
    RF_COMMAND_UNALIAS, 'u','n','a','l','i','a','s',0,
    RF_COMMAND_CONFIG, 'c','o','n','f','i','g',0,
    RF_COMMAND_DIR, 'd','i','r',0,
    RF_COMMAND_DIR, 'l','s',0,
    RF_COMMAND_TREE, 't','r','e','e',0,
    RF_COMMAND_STAT, 's','t','a','t',0,
    RF_COMMAND_VOLUME, 'v','o','l','u','m','e',0,
    RF_COMMAND_VOLUME, 'f','r','e','e',0,
    RF_COMMAND_MATCH, 'm','a','t','c','h',0,
    RF_COMMAND_TYPE, 't','y','p','e',0,
    RF_COMMAND_TYPE, 'c','a','t',0,
    RF_COMMAND_COPY, 'c','o','p','y',0,
    RF_COMMAND_COPY, 'c','p',0,
    RF_COMMAND_MOVE, 'm','o','v','e',0,
    RF_COMMAND_MOVE, 'm','v',0,
    RF_COMMAND_RENAME, 'r','e','n','a','m','e',0,
    RF_COMMAND_RENAME, 'r','e','n',0,
    RF_COMMAND_DELETE, 'd','e','l','e','t','e',0,
    RF_COMMAND_DELETE, 'r','m',0,
    RF_COMMAND_COMPARE, 'c','o','m','p','a','r','e',0,
    RF_COMMAND_COMPARE, 'v','e','r','i','f','y',0,
    RF_COMMAND_NEW, 'n','e','w',0,
    RF_COMMAND_WRITE, 'w','r','i','t','e',0,
    RF_COMMAND_APPEND, 'a','p','p','e','n','d',0,
    RF_COMMAND_MKDIR, 'm','k','d','i','r',0,
    RF_COMMAND_MKDIR, 'm','d',0,
    RF_COMMAND_RMDIR, 'r','m','d','i','r',0,
    RF_COMMAND_RMDIR, 'r','d',0,
    RF_COMMAND_MOUNT, 'm','o','u','n','t',0,
    RF_COMMAND_DISMOUNT, 'd','i','s','m','o','u','n','t',0,
    RF_COMMAND_DISMOUNT, 'u','n','m','o','u','n','t',0,
    RF_COMMAND_SWAP, 's','w','a','p',0,
    RF_COMMAND_CAPABILITIES,
        'c','a','p','a','b','i','l','i','t','i','e','s',0,
    RF_COMMAND_STATUS, 's','t','a','t','u','s',0,
    RF_COMMAND_FIND, 'f','i','n','d',0,
    RF_COMMAND_HEAD, 'h','e','a','d',0,
    RF_COMMAND_TAIL, 't','a','i','l',0,
    RF_COMMAND_CRC32, 'c','r','c','3','2',0,
    RF_COMMAND_TEST, 't','e','s','t',0,
    RF_COMMAND_RUN, 'r','u','n',0,
#ifndef READYFS_MONOLITHIC
    RF_COMMAND_IEC, 'i','e','c',0,
#endif
    RF_COMMAND_MOUNT, 'f','o','r','m','a','t',0,
    RF_COMMAND_FILE_PRG, 'p','r','g',0,
    RF_COMMAND_FILE_USR, 'u','s','r',0,
    RF_COMMAND_FILE_SEQ, 's','e','q',0,
    0
};

unsigned char readyfs_command_id(const char *word) {
    const unsigned char *entry;
    unsigned char id;
    entry = command_names;
    while (*entry != 0u) {
        id = *entry++;
        if (same_word(word, (const char *)entry)) return id;
        while (*entry++ != 0u) {}
    }
    return RF_COMMAND_UNKNOWN;
}
