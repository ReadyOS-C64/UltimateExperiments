#ifndef READYFS_VOLUME_H
#define READYFS_VOLUME_H
#include "readyfs_path.h"
typedef struct {
    const ReadyFsPath *path;
    const char *text;
    const char *directory;
    unsigned char *status;
} ReadyFsVolumeCall;
void readyfs_volume(ReadyFsVolumeCall *call);
unsigned char readyfs_overlay_volume(ReadyFsVolumeCall *call);
#endif
