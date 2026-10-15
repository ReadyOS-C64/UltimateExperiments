#ifndef RSQL_REU_H
#define RSQL_REU_H

#include "rsql_types.h"

#define RSQL_REU_MIN_KIB          512u
#define RSQL_REU_MAX_KIB        16384u
#define RSQL_REU_PAGE_SIZE        256u
#define RSQL_REU_ADMIN_CACHE_PAGE  34u
#define RSQL_REU_ADMIN_CACHE_PAGES 68u
#define RSQL_REU_SYSTEM_PAGES     102u
#define RSQL_REU_OVERLAY_PAGES    544u
#define RSQL_REU_JOURNAL_PAGES     16u

typedef struct RsqlReuConfig {
    rsql_u16 size_kib;
    rsql_u8 probe_hardware;
} RsqlReuConfig;

rsql_u8 rsql_reu_init(const RsqlReuConfig* config);
rsql_u8 rsql_reu_probe(rsql_u16* size_kib_out);
rsql_u16 rsql_reu_size_kib(void);
unsigned long rsql_reu_page_count(void);
rsql_u8 rsql_reu_read(unsigned long address, void* destination, rsql_u16 length);
rsql_u8 rsql_reu_write(unsigned long address, const void* source, rsql_u16 length);
rsql_u8 rsql_reu_compare(unsigned long address, const void* source, rsql_u16 length);
rsql_u8 rsql_reu_read_byte(unsigned long address, rsql_u8* value);
rsql_u8 rsql_reu_write_byte(unsigned long address, rsql_u8 value);
unsigned long rsql_reu_page_address(rsql_u16 page);

#endif
