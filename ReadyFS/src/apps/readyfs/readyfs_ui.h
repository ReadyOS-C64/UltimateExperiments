#ifndef READYFS_UI_H
#define READYFS_UI_H
#include "readyfs_batch.h"
#include "readyfs_tree.h"
unsigned char readyfs_ui_prepare(ReadyFsTreeCall *call);
unsigned char readyfs_ui_editor(ReadyFsBatchCall *call);
#endif
