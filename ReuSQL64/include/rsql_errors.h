#ifndef RSQL_ERRORS_H
#define RSQL_ERRORS_H

#define RSQL_OK                         0u
#define RSQL_ERR_REU_NOT_FOUND          1u
#define RSQL_ERR_REU_TOO_SMALL          2u
#define RSQL_ERR_INVALID_ARGUMENT       3u
#define RSQL_ERR_CORRUPT_STORAGE        4u
#define RSQL_ERR_OUT_OF_REU_PAGES       5u
#define RSQL_ERR_PAGE_RESERVED          6u
#define RSQL_ERR_NOT_IMPLEMENTED        7u
#define RSQL_ERR_ABI_MISMATCH           8u
#define RSQL_ERR_ALREADY_EXISTS         9u
#define RSQL_ERR_NOT_FOUND             10u
#define RSQL_ERR_SCHEMA_LIMIT          11u
#define RSQL_ERR_ROW_TOO_WIDE          12u
#define RSQL_ERR_BUFFER_TOO_SMALL      13u
#define RSQL_ERR_TYPE_MISMATCH         14u
#define RSQL_ERR_IO                    15u
#define RSQL_ERR_SYNTAX                16u
#define RSQL_ERR_UNSUPPORTED_SQL       17u
#define RSQL_ERR_CURSOR_STATE          18u
#define RSQL_ERR_JOURNAL_FULL          19u
#define RSQL_ERR_SUBQUERY_ROWS         20u
#define RSQL_ERR_DEPENDENT_OBJECT      21u
#define RSQL_ERR_NUMERIC_OVERFLOW      22u
#define RSQL_ERR_INTERNAL             255u

#endif
