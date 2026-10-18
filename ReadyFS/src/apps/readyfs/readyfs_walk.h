#ifndef READYFS_WALK_H
#define READYFS_WALK_H

#include "readyfs_plan.h"

#define RF_WALK_OK       0u
#define RF_WALK_DONE     1u
#define RF_WALK_BAD_NAME 2u
#define RF_WALK_TOO_DEEP 3u
#define RF_WALK_ERROR    4u

typedef struct {
    ReadyFsPlan *plan;
    unsigned int cursor;
    unsigned char max_depth;
} ReadyFsWalk;

void readyfs_walk_init(ReadyFsWalk *walk, ReadyFsPlan *plan,
                       unsigned char max_depth);
unsigned char readyfs_walk_seed(ReadyFsWalk *walk, unsigned char selected);
unsigned char readyfs_walk_next_directory(ReadyFsWalk *walk, char *stem,
                                          unsigned int stem_capacity,
                                          unsigned char *depth);
unsigned char readyfs_walk_add_child(ReadyFsWalk *walk, const char *parent,
                                     const char *name, unsigned char kind,
                                     unsigned char selected, char *output,
                                     unsigned int output_capacity);

#endif
