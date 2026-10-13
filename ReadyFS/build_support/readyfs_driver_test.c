#include <stdio.h>

#include "src/apps/readyfs/readyfs_driver.h"
#include "src/apps/readyfs/readyfs_cmdpath.h"

static int fails;

static void check(const char *status, unsigned char kind,
                  unsigned char flags) {
    ReadyFsDriverCall call;
    call.status = status;
    if (!readyfs_driver_classify(&call) || call.kind != kind ||
        call.flags != flags) {
        fprintf(stderr, "FAIL driver status %s\n", status);
        ++fails;
    }
}

int main(void) {
    unsigned char full;
    check("73,SD2IEC V1.0.0,00,00", RF_DRIVER_SD2IEC,
          RF_DRIVER_PARTITIONS | RF_DRIVER_FOLDERS | RF_DRIVER_IMAGES);
    check("73,CMD FD-2000 DOS V1.40,00,00", RF_DRIVER_CMD,
          RF_DRIVER_PARTITIONS | RF_DRIVER_FOLDERS);
    check("73,PI1541 V1.24,00,00", RF_DRIVER_PI1541, 0u);
    check("73,ULTIMATE 1541,00,00", RF_DRIVER_ULTIMATE, 0u);
    check("73,SOFTIEC,00,00", RF_DRIVER_SOFTIEC,
          RF_DRIVER_PARTITIONS | RF_DRIVER_FOLDERS | RF_DRIVER_IMAGES);
    check("73,VICE VIRTUAL DEVICE,00,00", RF_DRIVER_LEGACY, 0u);
    check("73,VIRTUAL DRIVE EMULATION V3.5,00,00", RF_DRIVER_LEGACY, 0u);
    check("00,OK,00,00", RF_DRIVER_UNKNOWN, 0u);
    full = RF_DRIVER_PARTITIONS | RF_DRIVER_FOLDERS | RF_DRIVER_IMAGES;
    if (!readyfs_driver_allows_operation(full, RF_CMDPATH_OPEN_FILE) ||
        !readyfs_driver_allows_operation(full, RF_CMDPATH_DIRECTORY) ||
        !readyfs_driver_allows_operation(full, RF_CMDPATH_SCRATCH) ||
        !readyfs_driver_allows_operation(full, RF_CMDPATH_MKDIR) ||
        !readyfs_driver_allows_operation(full, RF_CMDPATH_RMDIR) ||
        !readyfs_driver_allows_operation(full, RF_CMDPATH_RENAME) ||
        !readyfs_driver_allows_operation(full, RF_CMDPATH_MOUNT) ||
        !readyfs_driver_allows_operation(full, RF_CMDPATH_UNMOUNT) ||
        readyfs_driver_allows_operation(0u, RF_CMDPATH_OPEN_FILE) ||
        !readyfs_driver_allows_operation(
            RF_DRIVER_PARTITIONS | RF_DRIVER_FOLDERS,
            RF_CMDPATH_DIRECTORY) ||
        readyfs_driver_allows_operation(
            RF_DRIVER_PARTITIONS | RF_DRIVER_FOLDERS,
            RF_CMDPATH_MOUNT) ||
        readyfs_driver_allows_operation(full, 0u)) {
        fprintf(stderr, "FAIL driver operation capability matrix\n");
        ++fails;
    }
    if (fails != 0) return 1;
    puts("readyfs driver classification tests passed");
    return 0;
}
