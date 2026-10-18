#ifndef READYFS_TREE_H
#define READYFS_TREE_H

#define RF_TREE_ABI 0x5254u

#define RF_TREE_CALL_INIT 0x11u
#define RF_TREE_CALL_NEXT 0x12u
#define RF_TREE_CALL_ADD  0x13u
#define RF_TREE_CALL_REPORT 0x14u
#define RF_TREE_CALL_STATUS 0x15u
#define RF_TREE_CALL_COMMAND_ID 0x16u

#define RF_STATUS_REU     0x0001u
#define RF_STATUS_OVERLAY 0x0002u
#define RF_STATUS_PLAN    0x0004u
#define RF_STATUS_JOURNAL 0x0008u
#define RF_STATUS_BACKEND 0x0010u
#define RF_STATUS_UTILITY 0x0020u
#define RF_STATUS_TREE    0x0040u
#define RF_STATUS_BATCH   0x0080u

#define RF_TREE_OK       0u
#define RF_TREE_DONE     1u
#define RF_TREE_BAD_NAME 2u
#define RF_TREE_TOO_DEEP 3u
#define RF_TREE_FULL     4u
#define RF_TREE_CORRUPT  5u

#define RF_TREE_KIND_FILE 1u
#define RF_TREE_KIND_DIR  2u

typedef struct {
    unsigned char operation;
    unsigned char kind;
    unsigned char max_depth;
    unsigned char depth;
    unsigned char selected;
    unsigned char display;
    unsigned char result;
    const char *parent;
    const char *name;
    char *output;
    unsigned int output_capacity;
    char *relative;
    unsigned int relative_capacity;
    unsigned int limit;
    unsigned int entries;
    unsigned int files;
    unsigned int directories;
    unsigned int selected_entries;
    unsigned int queue_used;
    char **command_args;
    unsigned char command_argc;
} ReadyFsTreeCall;

unsigned int readyfs_tree_abi(void);
unsigned char readyfs_tree_dispatch(ReadyFsTreeCall *call);

#endif
