#include "storage_layout.h"

rsql_u16 rsql_get_u16(const rsql_u8* bytes) {
    return (rsql_u16)((rsql_u16)bytes[0] | ((rsql_u16)bytes[1] << 8u));
}

void rsql_put_u16(rsql_u8* bytes, rsql_u16 value) {
    bytes[0] = (rsql_u8)(value & 0xFFu);
    bytes[1] = (rsql_u8)(value >> 8u);
}

unsigned long rsql_get_u32(const rsql_u8* bytes) {
    return (unsigned long)bytes[0] |
           ((unsigned long)bytes[1] << 8u) |
           ((unsigned long)bytes[2] << 16u) |
           ((unsigned long)bytes[3] << 24u);
}

void rsql_put_u32(rsql_u8* bytes, unsigned long value) {
    bytes[0] = (rsql_u8)(value & 0xFFul);
    bytes[1] = (rsql_u8)((value >> 8u) & 0xFFul);
    bytes[2] = (rsql_u8)((value >> 16u) & 0xFFul);
    bytes[3] = (rsql_u8)((value >> 24u) & 0xFFul);
}

void rsql_increment_u32(rsql_u8* bytes) {
    rsql_u8 i;
    for (i = 0u; i < 4u; ++i) {
        ++bytes[i];
        if (bytes[i] != 0u) break;
    }
}

void rsql_decrement_u32(rsql_u8* bytes) {
    rsql_u8 i;
    for (i = 0u; i < 4u; ++i) {
        rsql_u8 before = bytes[i];
        --bytes[i];
        if (before != 0u) break;
    }
}

rsql_u8 rsql_page_checksum(const rsql_u8* page) {
    rsql_u8 checksum = 0x6Du;
    rsql_u16 i;
    for (i = 0u; i < RSQL_PAGE_CHECKSUM_OFFSET; ++i) checksum ^= page[i];
    return checksum;
}
