#ifndef RSQL_ENUM_H
#define RSQL_ENUM_H

#include "rsql_types.h"

#define RSQL_ENUM_NAME_MAX 24u
#define RSQL_ENUM_MEMBER_NAME_MAX 15u

typedef struct RsqlEnumMemberDefinition {
    const char* name;
    rsql_u16 value;
} RsqlEnumMemberDefinition;

typedef struct RsqlCreateEnumRequest {
    const char* name;
    rsql_u8 width;
    rsql_u8 member_count;
    const RsqlEnumMemberDefinition* members;
    rsql_u16 enum_id;
} RsqlCreateEnumRequest;

typedef struct RsqlEnumInfo {
    rsql_u16 enum_id;
    rsql_u16 enum_page;
    rsql_u16 member_count;
    rsql_u8 width;
    rsql_u8 name_length;
    char name[RSQL_ENUM_NAME_MAX + 1u];
} RsqlEnumInfo;

rsql_u8 rsql_enum_create(RsqlCreateEnumRequest* request);
rsql_u8 rsql_enum_find(const char* name, RsqlEnumInfo* info_out);
rsql_u8 rsql_enum_member_value(rsql_u16 enum_id, const char* member,
                               rsql_u16* value_out);
rsql_u8 rsql_enum_member_name(rsql_u16 enum_id, rsql_u16 value,
                              char* destination, rsql_u8 capacity);

#endif
