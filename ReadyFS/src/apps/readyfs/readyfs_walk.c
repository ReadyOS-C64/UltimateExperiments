#include "readyfs_walk.h"

#include <string.h>

static unsigned char stem_depth(const char *stem) {
    unsigned char depth;

    depth = stem[0] == 0 ? 0u : 1u;
    while (*stem != 0) if (*stem++ == '/') ++depth;
    return depth;
}

void readyfs_walk_init(ReadyFsWalk *walk, ReadyFsPlan *plan,
                       unsigned char max_depth) {
    if (walk == 0) return;
    walk->plan = plan;
    walk->cursor = RF_PLAN_END;
    walk->max_depth = max_depth == 0u ? 32u : max_depth;
}

unsigned char readyfs_walk_seed(ReadyFsWalk *walk, unsigned char selected) {
    if (walk == 0 || walk->plan == 0 ||
        !readyfs_plan_add(walk->plan, RF_PLAN_KIND_DIR,
                          selected ? RF_PLAN_SELECTED : 0u, "")) {
        return RF_WALK_ERROR;
    }
    walk->cursor = readyfs_plan_first(walk->plan);
    return RF_WALK_OK;
}

unsigned char readyfs_walk_next_directory(ReadyFsWalk *walk, char *stem,
                                          unsigned int stem_capacity,
                                          unsigned char *depth) {
    ReadyFsPlanRecord record;
    unsigned int next;

    if (walk == 0 || walk->plan == 0 || stem == 0 || depth == 0 ||
        stem_capacity == 0u) return RF_WALK_ERROR;
    while (walk->cursor < walk->plan->used) {
        unsigned int current;
        current = walk->cursor;
        if (!readyfs_plan_read(walk->plan, walk->cursor, &record, stem,
                               stem_capacity, &next)) return RF_WALK_ERROR;
        walk->cursor = (unsigned int)(current + 6u + record.stem_len + 1u);
        if (record.kind == RF_PLAN_KIND_DIR) {
            *depth = stem_depth(stem);
            return RF_WALK_OK;
        }
    }
    return RF_WALK_DONE;
}

unsigned char readyfs_walk_add_child(ReadyFsWalk *walk, const char *parent,
                                     const char *name, unsigned char kind,
                                     unsigned char selected, char *output,
                                     unsigned int output_capacity) {
    unsigned int parent_len;
    unsigned int name_len;
    unsigned int length;
    unsigned char depth;

    if (walk == 0 || walk->plan == 0 || parent == 0 || name == 0 ||
        output == 0 || output_capacity == 0u || name[0] == 0 ||
        strchr(name, '/') != 0 || strchr(name, '!') != 0 ||
        strcmp(name, ".") == 0 || strcmp(name, "..") == 0 ||
        (kind != RF_PLAN_KIND_FILE && kind != RF_PLAN_KIND_DIR)) {
        return RF_WALK_BAD_NAME;
    }
    parent_len = strlen(parent);
    name_len = strlen(name);
    length = (unsigned int)(parent_len + name_len +
                            (parent_len == 0u ? 0u : 1u));
    if (length + 1u > output_capacity || length > 255u) {
        return RF_WALK_BAD_NAME;
    }
    depth = (unsigned char)(stem_depth(parent) + 1u);
    if (kind == RF_PLAN_KIND_DIR && depth > walk->max_depth) {
        return RF_WALK_TOO_DEEP;
    }
    if (parent_len != 0u) {
        memcpy(output, parent, parent_len);
        output[parent_len++] = '/';
    }
    memcpy(output + parent_len, name, name_len + 1u);
    if (!readyfs_plan_add(walk->plan, kind,
                          selected ? RF_PLAN_SELECTED : 0u, output)) {
        return RF_WALK_ERROR;
    }
    return RF_WALK_OK;
}
