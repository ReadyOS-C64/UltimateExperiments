#ifndef RSQL_QUERY_H
#define RSQL_QUERY_H

#include "rsql_catalog.h"
#include "rsql_blob.h"
#include "rsql_enum.h"
#include "rsql.h"
#include "rsql_row.h"
#include "rsql_types.h"

#define RSQL_STMT_NONE          0u
#define RSQL_STMT_CREATE_TABLE  1u
#define RSQL_STMT_INSERT        2u
#define RSQL_STMT_SELECT        3u
#define RSQL_STMT_DELETE        4u
#define RSQL_STMT_UPDATE        5u
#define RSQL_STMT_CREATE_ENUM   6u
#define RSQL_STMT_CREATE_INDEX  7u
#define RSQL_STMT_CREATE_TABLE_AS 8u
#define RSQL_STMT_DROP_TABLE    9u
#define RSQL_STMT_DROP_INDEX   10u
#define RSQL_STMT_DROP_ENUM    11u
#define RSQL_STMT_SHOW_DATABASE 12u
#define RSQL_STMT_SHOW_TABLES   13u
#define RSQL_STMT_SHOW_COLUMNS  14u
#define RSQL_STMT_SHOW_INDEXES  15u
#define RSQL_STMT_SHOW_TYPES    16u
#define RSQL_STMT_SHOW_MEMBERS  17u

#define RSQL_ENUM_MEMBERS_MAX  16u

#define RSQL_SELECT_SCAN        1u
#define RSQL_SELECT_AGGREGATE   2u

#define RSQL_JOIN_NONE          0u
#define RSQL_JOIN_INNER         1u
#define RSQL_JOIN_LEFT          2u
#define RSQL_JOIN_CROSS         3u

#define RSQL_SOURCE_INNER       0x80u
#define RSQL_SOURCE_SUBQUERY    0x40u
#define RSQL_SOURCE_COLUMN_MASK 0x07u

#define RSQL_AGG_NONE           0u
#define RSQL_AGG_COUNT_STAR     1u
#define RSQL_AGG_COUNT          2u
#define RSQL_AGG_SUM            3u
#define RSQL_AGG_AVG            4u
#define RSQL_AGG_MIN            5u
#define RSQL_AGG_MAX            6u

/* Projection opcodes share the aggregate byte. Scalar opcodes deliberately
 * start above the aggregate range so the resident cursor state needs no new
 * arrays. Literal-side bits apply to string scalar operands. */
#define RSQL_SCALAR_LENGTH              16u
#define RSQL_SCALAR_SUBSTR              17u
#define RSQL_SCALAR_CONCAT              18u
#define RSQL_SCALAR_STRING              19u
#define RSQL_PROJECTION_OP_MASK         31u
#define RSQL_PROJECTION_LITERAL_LEFT    32u
#define RSQL_PROJECTION_LITERAL_RIGHT   64u
#define RSQL_PROJECTION_IS_SCALAR(op) \
    (((op) & RSQL_PROJECTION_OP_MASK) >= RSQL_SCALAR_LENGTH)
#define RSQL_RESULT_SCALAR_PRESENT      128u
#define RSQL_SCALAR_LITERAL_DATA(result) \
    ((const rsql_u8*)&g_rsql_statement.enum_members[0][0] + \
     (rsql_u8)g_rsql_statement.group_columns[(result)][0])
#define RSQL_SCALAR_LITERAL_LENGTH(result) \
    ((rsql_u8)g_rsql_statement.group_columns[(result)][1])
/* ORDER descriptors share source bytes with joined column references. Bit 7
 * already selects the inner join source, so projection-backed ORDER keys use
 * otherwise-unused descriptor bit 6. */
#define RSQL_ORDER_PROJECTION            64u
#define RSQL_ORDER_PROJECTION_MASK        7u
#define RSQL_ORDER_PROJECTION_MARKER      1u
#define RSQL_VARIABLE_COMPARE_COMPLEX    32u
#define RSQL_VARIABLE_COMPARE_HANDLES    16u
#define RSQL_VARIABLE_COMPARE_SCALAR      8u
#define RSQL_VARIABLE_COMPARE_PREDICATE   9u
#define RSQL_VARIABLE_COMPARE_WIDE_SCALAR 10u
#define RSQL_VARIABLE_COMPARE_AGGREGATE_SCALAR 11u
#define RSQL_VARIABLE_COMPARE_INDEXED_JOIN_NEXT 12u
#define RSQL_AGGREGATE_SCALAR_BRIDGE_IDLE   0u
#define RSQL_AGGREGATE_SCALAR_BRIDGE_REPLAY 1u
#define RSQL_AGGREGATE_SCALAR_BRIDGE_ROW    2u
#define RSQL_AGGREGATE_SCALAR_BRIDGE_BIND   3u
/* Slot 5 temporarily overlays this many leading bytes of execution.columns
 * while streaming two blob values. Wide joins preserve that live schema in
 * parser scratch around HANDLE comparisons. */
#define RSQL_VARIABLE_COMPARE_STATE_BYTES 20u

#define RSQL_VALUE_NULL         0u
#define RSQL_VALUE_BOOLEAN      1u
#define RSQL_VALUE_INTEGER      2u
#define RSQL_VALUE_STRING       3u
#define RSQL_VALUE_BINARY       4u
#define RSQL_VALUE_ENUM         5u
#define RSQL_VALUE_FLOAT        6u
#define RSQL_VALUE_REFERENCE    7u
#define RSQL_VALUE_STRING_MAX  63u

#define RSQL_PRED_EQ           1u
#define RSQL_PRED_NE           2u
#define RSQL_PRED_LT           3u
#define RSQL_PRED_LE           4u
#define RSQL_PRED_GT           5u
#define RSQL_PRED_GE           6u
#define RSQL_PRED_IS_NULL      7u
#define RSQL_PRED_IS_NOT_NULL  8u
#define RSQL_PRED_LIKE         9u
#define RSQL_PRED_SUBQUERY    10u

#define RSQL_SUBQUERY_NONE     0u
#define RSQL_SUBQUERY_EXISTS   1u
#define RSQL_SUBQUERY_IN       2u
#define RSQL_SUBQUERY_SCALAR   3u
/* The SELECT-idle subquery vectors encode a second JOIN's ON program.  This
 * sentinel lets metadata load the third schema without growing resident
 * cursor state.  subquery_compare_op carries the second join type. */
#define RSQL_SUBQUERY_WIDE_JOIN 4u

#define RSQL_PREDICATES_MAX    8u
#define RSQL_BOOL_PROGRAM_MAX 24u
#define RSQL_BOOL_AND        0x80u
#define RSQL_BOOL_OR         0x81u
#define RSQL_BOOL_NOT        0x82u

typedef struct RsqlParsedColumn {
    char name[RSQL_COLUMN_NAME_MAX + 1u];
    RsqlTypeSpec type;
    char type_name[RSQL_ENUM_NAME_MAX + 1u];
} RsqlParsedColumn;

typedef struct RsqlParsedValue {
    rsql_u8 kind;
    rsql_u8 length;
    RsqlI64 integer;
    char string[RSQL_VALUE_STRING_MAX + 1u];
} RsqlParsedValue;

typedef struct RsqlParsedPredicate {
    rsql_u8 op;
    char column[RSQL_COLUMN_NAME_MAX + 1u];
    RsqlParsedValue value;
} RsqlParsedPredicate;

typedef struct RsqlBoundPredicate {
    rsql_u8 op;
    rsql_u8 column;
    RsqlParsedValue value;
} RsqlBoundPredicate;

typedef struct RsqlParsedStatement {
    rsql_u8 kind;
    rsql_u8 column_count;
    rsql_u8 value_count;
    rsql_u8 select_mode;
    rsql_u8 select_all;
    rsql_u8 projection_count;
    rsql_u8 group_count;
    rsql_u8 where_present;
    rsql_u8 predicate_count;
    rsql_u8 bool_program_count;
    rsql_u8 enum_width;
    rsql_u8 enum_member_count;
    rsql_u8 using_index;
    rsql_u8 join_type;
    rsql_u8 join_predicate_count;
    rsql_u8 join_bool_program_count;
    rsql_u8 subquery_kind;
    rsql_u8 subquery_compare_op;
    rsql_u8 subquery_predicate_count;
    rsql_u8 subquery_bool_program_count;
    rsql_u8 nested_exists;
    rsql_u8 nested_predicate_start;
    rsql_u8 nested_predicate_count;
    rsql_u8 nested_bool_program_count;
    rsql_u8 distinct;
    rsql_u8 order_count;
    rsql_u8 order_desc_mask;
    rsql_u8 limit_present;
    rsql_u16 limit;
    rsql_u16 offset;
    rsql_u16 error_offset;
    char table_name[RSQL_TABLE_NAME_MAX + 1u];
    char table_alias[RSQL_COLUMN_NAME_MAX + 1u];
    char join_table_name[RSQL_TABLE_NAME_MAX + 1u];
    char join_table_alias[RSQL_COLUMN_NAME_MAX + 1u];
    char subquery_table_name[RSQL_TABLE_NAME_MAX + 1u];
    char subquery_table_alias[RSQL_COLUMN_NAME_MAX + 1u];
    char index_name[RSQL_TABLE_NAME_MAX + 1u];
    char subquery_projection[RSQL_COLUMN_NAME_MAX + 1u];
    RsqlParsedColumn columns[RSQL_TABLE_COLUMNS_MAX];
    RsqlParsedValue values[RSQL_TABLE_COLUMNS_MAX];
    char projections[RSQL_TABLE_COLUMNS_MAX][RSQL_COLUMN_NAME_MAX + 1u];
    rsql_u8 projection_aggregate[RSQL_TABLE_COLUMNS_MAX];
    /* GROUP BY names share the packed enum/scalar-literal pool.  Retaining
     * only their byte offsets avoids a second 128-byte name matrix in the
     * fixed work BSS. */
    rsql_u8 aggregate_group_offsets[RSQL_TABLE_COLUMNS_MAX];
    /* Scalar projection scratch: second CONCAT operands and packed literal
     * offsets/lengths.  Keep it distinct from GROUP BY names above. */
    char group_columns[RSQL_TABLE_COLUMNS_MAX][RSQL_COLUMN_NAME_MAX + 1u];
    RsqlParsedPredicate predicates[RSQL_PREDICATES_MAX];
    rsql_u8 bool_program[RSQL_BOOL_PROGRAM_MAX];
    rsql_u8 subquery_bool_program[RSQL_BOOL_PROGRAM_MAX];
    char enum_members[RSQL_ENUM_MEMBERS_MAX][RSQL_COLUMN_NAME_MAX + 1u];
    rsql_u16 enum_values[RSQL_ENUM_MEMBERS_MAX];
} RsqlParsedStatement;

/* Wide CTAS has no enum declaration. Its 25-byte destination name starts
 * beyond the 15-byte wide-index iterator prefix, leaving projection[0]
 * independently bindable. */
#define RSQL_WIDE_CTAS_NAME(statement) \
    ((char*)&(statement).enum_members[1][0])

#define RSQL_NESTED_BOOL_PROGRAM \
    ((rsql_u8*)&g_rsql_statement.enum_values[0])

#define RSQL_AGGREGATE_GROUP_NAME(statement, index) \
    ((const char*)&(statement).enum_members[0][0] + \
        (statement).aggregate_group_offsets[(index)])

/* Once aggregate GROUP names are bound, their parser offsets are dead. Reuse
 * those eight bytes for ORDER descriptors so update_columns remains available
 * to source-to-source scalar projections for the cursor lifetime. */
#define RSQL_AGGREGATE_ORDER_COLUMNS \
    (g_rsql_statement.aggregate_group_offsets)

typedef struct RsqlExecutionState {
    rsql_u16 table_page;
    rsql_u16 row_width;
    rsql_u8 column_count;
    RsqlColumnInfo columns[RSQL_TABLE_COLUMNS_MAX];
    rsql_u8 row[240];
} RsqlExecutionState;

typedef struct RsqlScalarComparePart {
    rsql_u8 kind;
    const rsql_u8* data;
    rsql_u16 first_page;
    rsql_u16 next_page;
    rsql_u16 start;
    rsql_u16 length;
    rsql_u16 page_start;
    rsql_u16 page_used;
} RsqlScalarComparePart;

typedef struct RsqlScalarCompareValue {
    rsql_u8 is_null;
    rsql_u8 part_count;
    RsqlScalarComparePart parts[2];
} RsqlScalarCompareValue;

typedef struct RsqlCursorState {
    rsql_u8 active;
    rsql_u8 mode;
    rsql_u8 positioned;
    rsql_u8 finished;
    rsql_u8 result_column_count;
    rsql_u8 where_present;
    rsql_u8 predicate_count;
    rsql_u8 bool_program_count;
    rsql_u8 group_count;
    rsql_u8 aggregate_nulls;
    rsql_u8 source_column_count;
    rsql_u8 update_count;
    rsql_u8 update_variable;
    rsql_u8 update_scan_started;
    rsql_u8 update_next_valid;
    rsql_u8 using_index;
    rsql_u8 join_type;
    rsql_u8 join_predicate_count;
    rsql_u8 join_bool_program_count;
    rsql_u8 join_inner_column_count;
    rsql_u8 join_inner_null;
    rsql_u8 join_outer_started;
    rsql_u8 join_inner_started;
    rsql_u8 join_outer_matched;
    rsql_u8 join_outer_pending_advance;
    rsql_u8 subquery_kind;
    rsql_u8 subquery_projection;
    rsql_u8 subquery_column_count;
    rsql_u8 distinct;
    rsql_u8 order_count;
    rsql_u8 order_desc_mask;
    rsql_u8 limit_present;
    rsql_u16 limit;
    rsql_u16 offset;
    rsql_u16 skipped_rows;
    rsql_u16 returned_rows;
    rsql_u16 table_page;
    rsql_u16 join_table_page;
    rsql_u16 subquery_table_page;
    rsql_u16 blob_directory;
    rsql_u16 row_width;
    rsql_u16 join_row_width;
    rsql_u16 subquery_row_width;
    rsql_u16 index_page;
    rsql_u16 index_leaf_head;
    rsql_u16 index_leaf_page;
    rsql_u8 index_leaf_slot;
    RsqlRowId row_id;
    RsqlRowId join_row_id;
    RsqlRowId subquery_row_id;
    RsqlRowId update_next_row_id;
    rsql_u8 projection[RSQL_TABLE_COLUMNS_MAX];
    rsql_u8 projection_aggregate[RSQL_TABLE_COLUMNS_MAX];
    rsql_u8 group_columns[RSQL_TABLE_COLUMNS_MAX];
    rsql_u8 update_columns[RSQL_TABLE_COLUMNS_MAX];
    RsqlBoundPredicate predicates[RSQL_PREDICATES_MAX];
    rsql_u8 bool_program[RSQL_BOOL_PROGRAM_MAX];
    RsqlColumnInfo columns[RSQL_TABLE_COLUMNS_MAX];
    RsqlColumnInfo join_columns[RSQL_TABLE_COLUMNS_MAX];
    rsql_u8 row[240];
    rsql_u8 scan_row[240];
    RsqlI64 aggregate_values[RSQL_TABLE_COLUMNS_MAX];
    RsqlI64 aggregate_counts[RSQL_TABLE_COLUMNS_MAX];
} RsqlCursorState;

/* Binding has already copied runtime scalar bounds into the cursor. Keep the
 * predicate stream cursor in otherwise-idle parser enum scratch so a wide
 * query's third materialized row remains intact. */
#define RSQL_VARIABLE_PREDICATE_STATE \
    ((rsql_u8*)g_rsql_statement.enum_values)
extern rsql_u8 g_rsql_variable_predicate_mask;
extern rsql_u8 g_rsql_variable_predicate_source;
extern rsql_u8 g_rsql_variable_predicate_truth[RSQL_PREDICATES_MAX];
extern rsql_u8 g_rsql_variable_compare_source;
extern rsql_i8 g_rsql_variable_compare_result;
extern rsql_u8 g_rsql_variable_compare_kind;
extern rsql_u8 g_rsql_aggregate_scalar_bridge_mode;
extern rsql_u8 g_rsql_variable_compare_left[4];
extern rsql_u8 g_rsql_variable_compare_right[4];
/* Two-source joins keep their explicit index iterators in resident work RAM.
 * They cannot share parser scratch: scalar string literals and SUBSTR bounds
 * remain live for the lifetime of the cursor. */
extern rsql_u8 g_rsql_join_index_state[10];
extern RsqlCursorNextRequest* g_cursor_next_request;
#define RSQL_VARIABLE_PREDICATE_MASK \
    (g_rsql_variable_predicate_mask)
#define RSQL_VARIABLE_PREDICATE_SOURCE \
    (g_rsql_variable_predicate_source)
#define RSQL_VARIABLE_PREDICATE_TRUTH \
    (g_rsql_variable_predicate_truth)

extern RsqlParsedStatement g_rsql_statement;
extern RsqlExecutionState g_rsql_execution;
extern RsqlCursorState g_rsql_cursor;
void rsql_aggregate_reset_state(void);

#define RSQL_SCALAR_COMPARE_LEFT ((RsqlScalarCompareValue*) \
    ((rsql_u8*)g_rsql_execution.columns + 32u))
#define RSQL_SCALAR_COMPARE_RIGHT ((RsqlScalarCompareValue*) \
    ((rsql_u8*)RSQL_SCALAR_COMPARE_LEFT + sizeof(RsqlScalarCompareValue)))

rsql_u8 __fastcall__ rsql_query_parse(const char* sql, rsql_u16 length);
rsql_u8 rsql_query_prepare_result_table_phase(void);
rsql_u8 rsql_query_exec_prepare(void);
rsql_u8 rsql_query_bind_join_phase(void);
rsql_u8 rsql_query_bind_subquery_phase(void);
rsql_u8 rsql_query_bind_nested_admin_phase(void);
rsql_u8 rsql_query_bind_complex_phase(void);
rsql_u8 rsql_query_bind_result_phase(void);
rsql_u8 rsql_query_bind_wide_join_phase(void);
rsql_u8 rsql_query_create_phase(void);
rsql_u8 rsql_temp_cleanup_phase(void);
rsql_u8 __fastcall__ rsql_table_drop_phase(rsql_u16 table_page);
rsql_u8 __fastcall__ rsql_table_publish_phase(rsql_u16 table_page);
rsql_u8 rsql_query_drop_phase(void);
rsql_u8 rsql_query_bind_create_index(void);
rsql_u8 __fastcall__ rsql_query_bind_select(RsqlQueryOpenRequest* request);
rsql_u8 rsql_query_bind_delete(void);
rsql_u8 rsql_query_bind_update(void);
rsql_u8 rsql_query_resolve_enum_value(const RsqlColumnInfo* column,
                                      RsqlParsedValue* value);
rsql_u8 rsql_query_resolve_insert_enums(void);
rsql_u8 rsql_query_resolve_join_enums(void);
rsql_u8 rsql_query_create_blob_value(const RsqlColumnInfo* column,
                                     const RsqlParsedValue* value,
                                     RsqlBlobHandle* handle);
rsql_u8 rsql_query_materialize_insert(void);
rsql_u8 rsql_query_materialize_update(void);
rsql_u8 __fastcall__ rsql_query_variable_column_phase(
    RsqlCursorColumnRequest* request);
rsql_u8 __fastcall__ rsql_query_variable_read_phase(
    RsqlValueReadRequest* request);
rsql_u8 __fastcall__ rsql_query_delete_phase(RsqlI64* affected_rows);
rsql_u8 __fastcall__ rsql_query_delete_begin_phase(RsqlI64* affected_rows);
rsql_u8 rsql_query_delete_next_phase(void);
rsql_u8 __fastcall__ rsql_query_delete_apply_phase(RsqlI64* affected_rows);
rsql_u8 __fastcall__ rsql_query_update_phase(RsqlI64* affected_rows);
rsql_u8 __fastcall__ rsql_query_update_begin_phase(RsqlI64* affected_rows);
rsql_u8 rsql_query_update_next_phase(void);
rsql_u8 __fastcall__ rsql_query_update_apply_phase(RsqlI64* affected_rows);
rsql_u8 __fastcall__ rsql_query_cursor_next_phase(RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_aggregate_result_next_phase(
    RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_aggregate_predicate_phase(rsql_u8 matched);
rsql_u8 __fastcall__ rsql_query_join_aggregate_next_phase(
    RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_join_aggregate_result_next_phase(
    RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_join_aggregate_source_next_phase(
    RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_join_aggregate_source_next_phase_c(
    RsqlCursorNextRequest* request);
rsql_u8 rsql_query_join_aggregate_scalar_row_phase(void);
rsql_u8 rsql_query_join_aggregate_read(
    rsql_u16 table_page, rsql_u16 row_width, const RsqlRowId* row_id,
    rsql_u8* destination);
rsql_u8 __fastcall__ rsql_query_cursor_index_row_phase(
    RsqlCursorNextRequest* request);
rsql_u8 rsql_query_predicate_match_phase(void);
rsql_u8 rsql_query_variable_predicates_phase(void);
rsql_u8 rsql_query_variable_group_match_phase(void);
rsql_u8 rsql_query_variable_compare_phase(void);
rsql_u8 rsql_query_variable_scalar_compare_phase(void);
rsql_u8 __fastcall__ rsql_query_variable_compare_owner(rsql_u8 owner_slot);
rsql_u8 __fastcall__ rsql_query_join_next_phase(
    RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_join_predicate_phase(
    RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_join_result_next_phase(
    RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_subquery_next_phase(
    RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_wide_join_next_phase(
    RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_indexed_join_next_phase(
    RsqlCursorNextRequest* request);
rsql_u8 rsql_query_wide_restore_phase(void);
rsql_u8 __fastcall__ rsql_query_wide_result_next_phase(
    RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_result_next_phase(
    RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_result_next_dispatch(
    RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_query_scalar_column_phase(
    RsqlCursorColumnRequest* request);
rsql_u8 __fastcall__ rsql_query_scalar_read_phase(
    RsqlValueReadRequest* request);
void __fastcall__ rsql_query_scalar_variable_prepare(rsql_u8 result);
rsql_u8 __fastcall__ rsql_query_cursor_column_phase(RsqlCursorColumnRequest* request);
rsql_u8 __fastcall__ rsql_query_value_read_phase(RsqlValueReadRequest* request);
rsql_u8 __fastcall__ rsql_query_close_phase(RsqlQueryCloseRequest* request);

#endif
