#ifndef READYFS_IO_H
#define READYFS_IO_H

typedef struct {
    const char *source;
    const char *destination;
    unsigned char force;
    unsigned char move;
    unsigned char skip_verify;
} ReadyFsIoCopyCall;

unsigned char readyfs_io_copy_call(ReadyFsIoCopyCall *call);

#endif
