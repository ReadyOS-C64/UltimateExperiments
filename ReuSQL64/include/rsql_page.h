#ifndef RSQL_PAGE_H
#define RSQL_PAGE_H

#include "rsql_types.h"

#define RSQL_PAGE_NONE 0xFFFFu

rsql_u8 rsql_page_format(void);
rsql_u8 rsql_page_allocator_open(void);
rsql_u8 rsql_page_allocate(rsql_u16* page_out);
rsql_u8 rsql_page_free(rsql_u16 page);
rsql_u8 rsql_page_is_allocated(rsql_u16 page, rsql_u8* allocated_out);
rsql_u16 rsql_page_first_usable(void);
unsigned long rsql_page_limit(void);
rsql_u16 rsql_page_catalog_root(void);
rsql_u8 rsql_page_set_catalog_root(rsql_u16 page);

#endif
