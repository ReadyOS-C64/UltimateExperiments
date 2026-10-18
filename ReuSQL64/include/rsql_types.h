#ifndef RSQL_TYPES_H
#define RSQL_TYPES_H

typedef unsigned char rsql_u8;
typedef signed char rsql_i8;
typedef unsigned int rsql_u16;
typedef signed int rsql_i16;

typedef struct RsqlU24 {
    rsql_u8 lo;
    rsql_u8 mid;
    rsql_u8 hi;
} RsqlU24;

typedef struct RsqlI32 {
    rsql_u8 bytes[4];
} RsqlI32;

typedef struct RsqlI64 {
    rsql_u8 bytes[8];
} RsqlI64;

/* Stable SQL physical type tags. Values are part of the on-REU format. */
#define RSQL_TYPE_BOOLEAN   1u
#define RSQL_TYPE_I8        2u
#define RSQL_TYPE_I16       3u
#define RSQL_TYPE_I32       4u
#define RSQL_TYPE_I64       5u
#define RSQL_TYPE_FIXED8_8  6u
#define RSQL_TYPE_FLOAT5    7u
#define RSQL_TYPE_CHAR      8u
#define RSQL_TYPE_TEXT      9u
#define RSQL_TYPE_BLOB     10u
#define RSQL_TYPE_ENUM8    11u
#define RSQL_TYPE_ENUM16   12u

#define RSQL_TYPE_FLAG_NULLABLE 0x01u

typedef struct RsqlTypeSpec {
    rsql_u8 tag;
    rsql_u8 flags;
    /* CHAR length; zero for fixed-size scalar types. */
    rsql_u16 parameter;
    /* Enum catalog ID; zero for non-enum types. */
    rsql_u16 auxiliary;
} RsqlTypeSpec;

rsql_u8 rsql_type_width(const RsqlTypeSpec* type, rsql_u16* width_out);
rsql_u8 rsql_type_is_variable(const RsqlTypeSpec* type);
void __fastcall__ rsql_i64_clear(RsqlI64* value);
void __fastcall__ rsql_i64_increment(RsqlI64* value);

#endif
