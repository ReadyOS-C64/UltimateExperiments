#ifndef RSQL_SHELL_H
#define RSQL_SHELL_H

#include "rsql_types.h"

#define RSQL_SHELL_LINE_MAX 160u

typedef void (*RsqlShellWriteFn)(const char* bytes, rsql_u16 length,
                                 void* user);

typedef struct RsqlShell {
    RsqlShellWriteFn write;
    void* user;
    rsql_u8 device;
    rsql_u8 logical_file;
    rsql_u8 quit_requested;
} RsqlShell;

void rsql_shell_init(RsqlShell* shell, RsqlShellWriteFn write, void* user);
rsql_u8 rsql_shell_run_line(RsqlShell* shell, const char* line);

#endif
