#ifndef READYFS_PATH_H
#define READYFS_PATH_H

#define RF_PATH_MAX 255u

#define RF_EP_NONE     0u
#define RF_EP_IEC      1u
#define RF_EP_ULTIMATE 2u
#define RF_EP_SOFTIEC  3u
#define RF_EP_TAPE     4u
#define RF_EP_ALIAS    5u

#define RF_PATH_OK          0u
#define RF_PATH_EMPTY       1u
#define RF_PATH_TOO_LONG    2u
#define RF_PATH_BAD_ENDPOINT 3u
#define RF_PATH_BAD_DEVICE  4u
#define RF_PATH_BAD_SEGMENT 5u
#define RF_PATH_ESCAPE      6u

typedef struct {
    unsigned char endpoint;
    unsigned char unit;
    unsigned char partition;
    unsigned char absolute;
    unsigned char image_depth;
    unsigned char path_offset;
    unsigned char alias_len;
} ReadyFsPath;

unsigned char readyfs_path_parse(const char *text, ReadyFsPath *out);
unsigned char readyfs_path_normalize(const char *text, char *out);
unsigned char readyfs_path_has_parent_escape(const char *text);
const char *readyfs_path_error(unsigned char rc);

#endif
