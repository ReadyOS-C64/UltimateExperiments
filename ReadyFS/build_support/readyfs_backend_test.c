#include <stdio.h>
#include <string.h>

#include "src/apps/readyfs/readyfs_backend.h"
#include "src/apps/readyfs/readyfs_exec.h"

static int fails;

static void check(unsigned char truth, const char *message) {
    if (!truth) {
        fprintf(stderr, "FAIL backend %s\n", message);
        ++fails;
    }
}

static unsigned char build(ReadyFsBackendRequest *request,
                           unsigned char action, const char *source_root,
                           const char *destination_root, const char *stem) {
    ReadyFsBackendCall call;

    memset(&call, 0, sizeof(call));
    call.operation = RF_BACKEND_CALL_BUILD;
    call.action = action;
    call.source_root = source_root;
    call.destination_root = destination_root;
    call.stem = stem;
    call.request = request;
    return readyfs_backend_build(&call);
}

int main(void) {
    ReadyFsBackendRequest request;
    ReadyFsBackendCall call;
    ReadyFsBackendCapabilities capabilities;
    char source[256];
    char destination[256];
    char small[8];

    memset(&request, 0, sizeof(request));
    request.source_text = source;
    request.source_capacity = sizeof(source);
    request.destination_text = destination;
    request.destination_capacity = sizeof(destination);
    check(build(&request, RF_EXEC_ACTION_COPY_FILE,
                "8:/", "u:/usb1/out", "dir/a.prg") &&
          strcmp(source, "8:/dir/a.prg") == 0 &&
          strcmp(destination, "u:/usb1/out/dir/a.prg") == 0 &&
          request.source.endpoint == RF_EP_IEC && request.source.unit == 8u &&
          request.destination.endpoint == RF_EP_ULTIMATE &&
          request.has_source && request.has_destination,
          "cross-backend copy request");

    check(build(&request, RF_EXEC_ACTION_COPY_FILE,
                "u:/usb1/source.d81!", "s3:/backup/", "sub/file.seq") &&
          strcmp(source, "u:/usb1/source.d81!/sub/file.seq") == 0 &&
          strcmp(destination, "s3:/backup/sub/file.seq") == 0 &&
          request.source.image_depth == 1u &&
          request.destination.endpoint == RF_EP_SOFTIEC &&
          request.destination.unit == 3u,
          "image-to-softiec request");

    check(build(&request, RF_EXEC_ACTION_DELETE_FILE,
                "u:/usb1/tree", 0, "old/a.prg") &&
          request.has_source && !request.has_destination &&
          strcmp(source, "u:/usb1/tree/old/a.prg") == 0,
          "delete has source only");

    check(build(&request, RF_EXEC_ACTION_MKDIR,
                0, "u:/sd/tree", "new/sub") &&
          !request.has_source && request.has_destination &&
          strcmp(destination, "u:/sd/tree/new/sub") == 0,
          "mkdir has destination only");

    check(!build(&request, RF_EXEC_ACTION_COPY_FILE,
                 "8:/", "u:/usb1/out", "../escape"),
          "reject parent escape");
    check(!build(&request, RF_EXEC_ACTION_COPY_FILE,
                 "@work:/", "u:/usb1/out", "a.prg"),
          "reject unresolved alias");
    request.destination_text = small;
    request.destination_capacity = sizeof(small);
    check(!build(&request, RF_EXEC_ACTION_MKDIR, 0,
                 "u:/usb1/out", "too-long"),
          "bounded destination buffer");

    request.destination_text = destination;
    request.destination_capacity = sizeof(destination);
    memset(&call, 0, sizeof(call));
    call.operation = RF_BACKEND_CALL_BUILD;
    call.action = RF_EXEC_ACTION_MOVE_FILE;
    call.source_root = "11.3:/src";
    call.destination_root = "u:/sd/dest.d81!";
    call.stem = "nested/a.prg";
    call.request = &request;
    check(readyfs_backend_dispatch(&call) &&
          request.source.partition == 3u &&
          strcmp(destination, "u:/sd/dest.d81!/nested/a.prg") == 0,
          "dispatcher preserves partition and image context");
    check(!readyfs_backend_dispatch(0), "null dispatcher rejection");
    memset(&call, 0, sizeof(call));
    call.operation = RF_BACKEND_CALL_SELFTEST;
    check(readyfs_backend_dispatch(&call), "dispatcher selftest");
    call.operation = RF_BACKEND_CALL_CAPABILITIES;
    call.source_root = "t:/archive";
    call.capabilities = &capabilities;
    check(readyfs_backend_dispatch(&call) &&
          capabilities.endpoint == RF_EP_TAPE &&
          capabilities.leaf_limit == 16u &&
          capabilities.flags == (RF_CAP_READ | RF_CAP_WRITE |
                                  RF_CAP_SEQUENTIAL) &&
          capabilities.size_units == RF_SIZE_NONE &&
          !capabilities.provisional,
          "proven sequential tape model");
    call.source_root = "u:/usb1/tree.d81!/dir";
    check(readyfs_backend_dispatch(&call) &&
          (capabilities.flags & (RF_CAP_RECURSE | RF_CAP_IMAGES |
                                RF_CAP_MOUNT)) ==
              (RF_CAP_RECURSE | RF_CAP_IMAGES | RF_CAP_MOUNT) &&
          capabilities.size_units == RF_SIZE_BYTES &&
          !capabilities.provisional,
          "ultimate hierarchical capability model");
    call.source_root = "s3:/tree";
    check(readyfs_backend_dispatch(&call) && capabilities.unit == 3u &&
          capabilities.provisional &&
          (capabilities.flags & RF_CAP_RECURSE) == 0u,
          "softiec provisional capability model");
    call.source_root = "@work:/archive";
    check(!readyfs_backend_dispatch(&call), "capabilities reject alias");
    if (fails != 0) return 1;
    puts("readyfs backend tests passed");
    return 0;
}
