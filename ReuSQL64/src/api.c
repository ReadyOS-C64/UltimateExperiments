#include <string.h>

#include "rsql.h"
#include "rsql_blob.h"
#include "rsql_catalog.h"
#include "rsql_journal.h"
#include "rsql_index.h"
#include "rsql_overlay.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_query_phase.h"
#include "rsql_row.h"
#include "rsql_scratch.h"
#include "api_internal.h"

static const char MSG_OK[] = "OK";
static const char MSG_ABI[] = "ABI error";
static const char MSG_STORAGE[] = "Storage error";
static const char MSG_SYNTAX[] = "Syntax error";
static const char MSG_UNSUPPORTED[] = "Unsupported SQL";

static RsqlErrorInfo g_error = { RSQL_OK, 0u, MSG_OK };
static rsql_u16 g_insert_bind_table_page;
static rsql_u16 g_insert_bind_row_width;
static rsql_u8 g_insert_bind_column_count;
static RsqlQueryOpenRequest g_result_open;
static RsqlCursorNextRequest g_result_next;
RsqlCursorColumnRequest g_result_value;
static RsqlValueReadRequest g_result_read;
static RsqlQueryCloseRequest g_result_close;
RsqlColumnInfo g_result_destination;
RsqlBlobHandle g_result_handle;
RsqlRowId g_result_row_id;
static RsqlExecRequest* g_result_request;
static rsql_u16 g_result_offset;
rsql_u16 g_result_copy;
static rsql_u8 g_result_column;
static rsql_u8 g_result_rc;
static rsql_u8 g_result_close_rc;
static rsql_u8 g_result_transaction;
rsql_u16 g_result_table_page;
RsqlParsedStatement g_rsql_statement;
RsqlExecutionState g_rsql_execution;
RsqlCursorState g_rsql_cursor;
rsql_u8 g_rsql_meta_page0[RSQL_REU_PAGE_SIZE];
rsql_u8 g_rsql_meta_page1[RSQL_REU_PAGE_SIZE];

static rsql_u8 fail_at(rsql_u8 code, const char* message, rsql_u16 offset) {
    g_error.code = code;
    g_error.byte_offset = offset;
    g_error.message = message;
    return code;
}

static rsql_u8 fail(rsql_u8 code, const char* message) {
    return fail_at(code, message, 0u);
}

static rsql_u8 cleanup_temporary_tables(void) {
    rsql_u8 restore_rc;
    rsql_u8 rc = rsql_overlay_load(3u);
    if (rc == RSQL_OK) rc = rsql_temp_cleanup_phase();
    restore_rc = rsql_overlay_load(0u);
    return rc == RSQL_OK ? restore_rc : rc;
}

rsql_u8 rsql_api_error(rsql_u8 code, rsql_u16 offset) {
    if (code == RSQL_OK) return fail_at(code, MSG_OK, offset);
    if (code == RSQL_ERR_SYNTAX) return fail_at(code, MSG_SYNTAX, offset);
    if (code == RSQL_ERR_UNSUPPORTED_SQL) {
        return fail_at(code, MSG_UNSUPPORTED, offset);
    }
    return fail_at(code, MSG_STORAGE, offset);
}

static rsql_u8 restore_result_source(void) {
    rsql_u8 rc;
    if (g_rsql_statement.subquery_kind != RSQL_SUBQUERY_WIDE_JOIN) {
        g_result_read.destination = g_rsql_execution.row;
        g_result_read.capacity = sizeof(g_rsql_execution.row);
        return RSQL_OK;
    }
    g_result_read.destination = (rsql_u8*)g_rsql_cursor.aggregate_values;
    g_result_read.capacity = sizeof(g_rsql_cursor.aggregate_values);
    rc = rsql_overlay_load(7u);
    return rc == RSQL_OK ? rsql_query_wide_restore_phase() : rc;
}

static rsql_u8 materialize_result_table(RsqlExecRequest* request) {
    g_result_request = request;
    g_result_transaction = 0u;
    g_result_table_page = RSQL_PAGE_NONE;
    memset(&g_result_open, 0, sizeof(g_result_open));
    g_result_rc = rsql_query_open_parsed(&g_result_open);
    if (g_result_rc != RSQL_OK) return g_result_rc;
    g_result_rc = rsql_overlay_load(7u);
    if (g_result_rc == RSQL_OK) {
        g_result_rc = rsql_query_prepare_result_table_phase();
    }
    if (g_result_rc == RSQL_OK) {
        g_result_rc = rsql_journal_begin();
        if (g_result_rc == RSQL_OK) g_result_transaction = 1u;
    }
    if (g_result_rc == RSQL_OK) g_result_rc = rsql_overlay_load(0u);
    if (g_result_rc == RSQL_OK) g_result_rc = rsql_query_create_phase();
    if (g_result_rc == RSQL_OK) {
        g_result_table_page = g_rsql_execution.table_page;
        if (g_rsql_statement.subquery_kind == RSQL_SUBQUERY_WIDE_JOIN) {
            g_rsql_execution.table_page = g_rsql_cursor.subquery_table_page;
            g_rsql_execution.row_width = g_rsql_cursor.subquery_row_width;
            g_rsql_execution.column_count =
                g_rsql_cursor.subquery_column_count;
        }
    }
    if (g_result_transaction) {
        g_result_rc = rsql_finish_mutation(g_result_rc);
        g_result_transaction = 0u;
    }

    g_result_next.cursor = 1u;
    while (g_result_rc == RSQL_OK) {
        g_result_rc = rsql_cursor_next(&g_result_next);
        if (g_result_rc != RSQL_OK || !g_result_next.has_row) break;
        g_result_rc = rsql_journal_begin();
        if (g_result_rc == RSQL_OK) g_result_transaction = 1u;
        memset(g_rsql_execution.row, 0, g_rsql_statement.error_offset);
        if (g_result_rc == RSQL_OK) g_result_rc = rsql_overlay_load(1u);
        if (g_result_rc == RSQL_OK) {
            g_result_rc = rsql_row_insert(g_result_table_page,
                g_rsql_execution.row, g_rsql_statement.error_offset,
                &g_result_row_id);
        }
        for (g_result_column = 0u;
             g_result_rc == RSQL_OK &&
                 g_result_column < g_rsql_cursor.result_column_count;
            ++g_result_column) {
            g_result_rc = restore_result_source();
            if (g_result_rc == RSQL_OK) g_result_rc = rsql_overlay_load(0u);
            if (g_result_rc == RSQL_OK) {
                g_result_rc = rsql_column_info(g_result_table_page,
                    g_result_column, &g_result_destination);
            }
            g_result_value.cursor = 1u;
            g_result_value.column = g_result_column;
            if (g_result_rc == RSQL_OK) {
                g_result_rc = rsql_cursor_column(&g_result_value);
            }
            if (g_result_rc != RSQL_OK) break;
            if (g_result_value.value.is_null) {
            } else if (g_result_value.value.type.tag == RSQL_TYPE_TEXT ||
                       g_result_value.value.type.tag == RSQL_TYPE_BLOB) {
                g_result_rc = rsql_overlay_load(0u);
                if (g_result_rc == RSQL_OK) {
                    g_result_rc = rsql_blob_create(
                        g_result_value.value.type.tag, 0, 0u,
                        &g_result_handle);
                }
            } else {
                g_result_read.cursor = 1u;
                g_result_read.column = g_result_column;
                g_result_read.offset = 0u;
                g_result_read.destination = g_rsql_meta_page0;
                g_result_read.capacity =
                    g_result_destination.type.tag == RSQL_TYPE_CHAR
                    ? g_result_destination.type.parameter
                    : g_result_value.value.length;
                g_result_read.bytes_read = 0u;
                g_result_rc = rsql_value_read(&g_result_read);
                if (g_result_rc != RSQL_OK) break;
                g_result_copy = g_result_read.bytes_read;
            }
            if (g_result_rc == RSQL_OK) g_result_rc = rsql_overlay_load(1u);
            if (g_result_rc == RSQL_OK) g_result_rc = rsql_ctas_patch_phase();
        }
        if (g_result_transaction) {
            g_result_rc = rsql_finish_mutation(g_result_rc);
            g_result_transaction = 0u;
        }
        for (g_result_column = 0u;
             g_result_rc == RSQL_OK &&
                 g_result_column < g_rsql_cursor.result_column_count;
             ++g_result_column) {
            g_result_rc = rsql_overlay_load(0u);
            if (g_result_rc == RSQL_OK) {
                g_result_rc = rsql_column_info(g_result_table_page,
                    g_result_column, &g_result_destination);
            }
            if (g_result_rc != RSQL_OK ||
                (g_result_destination.type.tag != RSQL_TYPE_TEXT &&
                 g_result_destination.type.tag != RSQL_TYPE_BLOB)) continue;
            g_result_rc = rsql_overlay_load(1u);
            if (g_result_rc == RSQL_OK) {
                g_result_rc = rsql_row_read(g_result_table_page,
                    &g_result_row_id, g_rsql_execution.row,
                    sizeof(g_rsql_execution.row));
            }
            if (g_result_rc != RSQL_OK) break;
            if (g_rsql_execution.row[g_result_column >> 3u] &
                (rsql_u8)(1u << (g_result_column & 7u))) continue;
            memcpy(g_result_handle.bytes,
                   &g_rsql_execution.row[g_result_destination.offset],
                   sizeof(g_result_handle.bytes));
            g_result_rc = restore_result_source();
            g_result_value.cursor = 1u;
            g_result_value.column = g_result_column;
            if (g_result_rc == RSQL_OK) {
                g_result_rc = rsql_cursor_column(&g_result_value);
            }
            g_result_offset = 0u;
            while (g_result_rc == RSQL_OK &&
                   g_result_offset < g_result_value.value.length) {
                g_result_copy = (rsql_u16)
                    (g_result_value.value.length - g_result_offset);
                if (g_result_copy > g_result_read.capacity) {
                    g_result_copy = g_result_read.capacity;
                }
                g_result_read.cursor = 1u;
                g_result_read.column = g_result_column;
                g_result_read.offset = g_result_offset;
                g_result_read.bytes_read = 0u;
                g_result_rc = rsql_value_read(&g_result_read);
                if (g_result_rc == RSQL_OK &&
                    g_result_read.bytes_read == 0u) {
                    g_result_rc = RSQL_ERR_CORRUPT_STORAGE;
                }
                if (g_result_rc == RSQL_OK) {
                    g_result_rc = rsql_overlay_load(3u);
                }
                if (g_result_rc == RSQL_OK) {
                    g_result_rc = rsql_blob_append(&g_result_handle,
                        g_result_read.destination,
                        g_result_read.bytes_read);
                }
                g_result_offset = (rsql_u16)
                    (g_result_offset + g_result_read.bytes_read);
            }
        }
        if (g_result_rc == RSQL_OK) {
            rsql_i64_increment(&g_result_request->output.affected_rows);
        }
    }
    g_result_close.cursor = 1u;
    g_result_close_rc = rsql_query_close(&g_result_close);
    if (g_result_rc == RSQL_OK && g_result_close_rc != RSQL_OK) {
        g_result_rc = g_result_close_rc;
    }
    if (g_result_rc == RSQL_OK) {
        g_result_rc = rsql_overlay_load(3u);
        if (g_result_rc == RSQL_OK) {
            g_result_rc = rsql_table_publish_phase(g_result_table_page);
        }
    }
    if (g_result_rc != RSQL_OK && g_result_table_page != RSQL_PAGE_NONE) {
        g_result_close_rc = g_result_rc;
        if (rsql_overlay_load(3u) == RSQL_OK) {
            rsql_table_drop_phase(g_result_table_page);
        }
        g_result_rc = g_result_close_rc;
    }
    return g_result_rc;
}

static rsql_u8 execute_bound_mutation(RsqlExecRequest* request) {
    rsql_u8 deleting = g_rsql_statement.kind == RSQL_STMT_DELETE;
    rsql_u8 rc = deleting
        ? rsql_query_delete_begin_phase(&request->output.affected_rows)
        : rsql_query_update_begin_phase(&request->output.affected_rows);
    while (rc == RSQL_OK) {
        rc = deleting ? rsql_query_delete_next_phase()
                      : rsql_query_update_next_phase();
        if (rc == RSQL_ERR_NOT_FOUND) return RSQL_OK;
        if (rc == RSQL_QUERY_PHASE_PREDICATE) {
            rc = rsql_query_variable_predicate_test();
            if (rc == RSQL_QUERY_PHASE_INDEX_SKIP) {
                rc = RSQL_OK;
                continue;
            }
        }
        if (rc == RSQL_OK && !deleting && g_rsql_cursor.update_variable) {
            rc = rsql_overlay_load(0u);
            if (rc == RSQL_OK) rc = rsql_query_materialize_update();
            if (rc == RSQL_OK) rc = rsql_overlay_load(1u);
        }
        if (rc == RSQL_OK) {
            rc = deleting
                ? rsql_query_delete_apply_phase(&request->output.affected_rows)
                : rsql_query_update_apply_phase(&request->output.affected_rows);
        }
    }
    return rc;
}

rsql_u16 rsql_api_version(void) {
    return (rsql_u16)(((rsql_u16)RSQL_ABI_MAJOR << 8u) | RSQL_ABI_MINOR);
}

rsql_u8 __fastcall__ rsql_init(RsqlInitRequest* request) {
    rsql_u8 rc;
    rsql_u8 formatted = 0u;
    if (!request) return fail(RSQL_ERR_INVALID_ARGUMENT, MSG_STORAGE);
    if (request->abi_major != RSQL_ABI_MAJOR) {
        return fail(RSQL_ERR_ABI_MISMATCH, MSG_ABI);
    }
    rc = rsql_reu_init(&request->reu);
    if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
    rc = rsql_page_allocator_open();
    if (rc == RSQL_ERR_CORRUPT_STORAGE && request->format_if_missing) {
        rc = rsql_page_format();
        if (rc == RSQL_OK) rc = rsql_page_allocator_open();
        formatted = 1u;
    }
    if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
    rc = rsql_overlay_init();
    if (rc == RSQL_OK && request->preloaded_overlay_mask != 0u) {
        rc = rsql_overlay_mark_valid(request->preloaded_overlay_mask);
    } else if (rc == RSQL_OK) {
        rc = rsql_overlay_bootstrap_disk();
    }
    if (rc == RSQL_OK) rc = rsql_overlay_load(0u);
    if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
    rc = formatted ? rsql_catalog_format() : rsql_catalog_open();
    if (rc == RSQL_OK) rc = cleanup_temporary_tables();
    if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
    return fail(RSQL_OK, MSG_OK);
}

rsql_u8 rsql_shutdown(void) {
    rsql_u8 rc = cleanup_temporary_tables();
    return fail(rc, rc == RSQL_OK ? MSG_OK : MSG_STORAGE);
}

rsql_u8 __fastcall__ rsql_exec(RsqlExecRequest* request) {
    RsqlTableInfo table;
    RsqlRowId row_id;
    rsql_u8 index;
    rsql_u8 rc;
    if (!request || !request->sql) {
        return fail(RSQL_ERR_INVALID_ARGUMENT, MSG_UNSUPPORTED);
    }
    rc = rsql_overlay_load(2u);
    if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
    rc = rsql_query_parse(request->sql, request->sql_length);
    if (rc == RSQL_ERR_SYNTAX) {
        return fail_at(rc, MSG_SYNTAX, g_rsql_statement.error_offset);
    }
    if (rc == RSQL_ERR_UNSUPPORTED_SQL) {
        return fail_at(rc, MSG_UNSUPPORTED, g_rsql_statement.error_offset);
    }
    if (rc != RSQL_OK) return fail(rc, MSG_SYNTAX);

    if (g_rsql_statement.kind >= RSQL_STMT_SHOW_DATABASE &&
        g_rsql_statement.kind <= RSQL_STMT_SHOW_MEMBERS) {
        request->output.inspect.returned = 0u;
        rc = rsql_overlay_load_admin();
        if (rc == RSQL_OK) rc = rsql_inspect_phase(request);
        if (rsql_overlay_load(0u) != RSQL_OK && rc == RSQL_OK) {
            rc = RSQL_ERR_IO;
        }
        return fail(rc, rc == RSQL_OK ? MSG_OK : MSG_STORAGE);
    }

    rsql_i64_clear(&request->output.affected_rows);

    if (g_rsql_statement.kind == RSQL_STMT_CREATE_TABLE ||
        g_rsql_statement.kind == RSQL_STMT_CREATE_ENUM) {
        rc = rsql_overlay_load(0u);
        if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        rc = rsql_journal_begin();
        if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        rc = rsql_query_create_phase();
        rc = rsql_finish_mutation(rc);
        return fail(rc, rc == RSQL_OK ? MSG_OK : MSG_STORAGE);
    }
    if (g_rsql_statement.kind == RSQL_STMT_CREATE_TABLE_AS) {
        rc = materialize_result_table(request);
        return fail(rc, rc == RSQL_OK ? MSG_OK :
            (rc == RSQL_ERR_UNSUPPORTED_SQL ? MSG_UNSUPPORTED : MSG_STORAGE));
    }
    if (g_rsql_statement.kind == RSQL_STMT_CREATE_INDEX) {
        rc = rsql_overlay_load(0u);
        if (rc == RSQL_OK) rc = rsql_query_bind_create_index();
        if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        rc = rsql_journal_begin();
        if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        rc = rsql_overlay_load(3u);
        if (rc == RSQL_OK) rc = rsql_index_create_phase();
        rc = rsql_finish_mutation(rc);
        return fail(rc, rc == RSQL_OK ? MSG_OK : MSG_STORAGE);
    }
    if (g_rsql_statement.kind == RSQL_STMT_DROP_TABLE ||
        g_rsql_statement.kind == RSQL_STMT_DROP_INDEX ||
        g_rsql_statement.kind == RSQL_STMT_DROP_ENUM) {
        rc = rsql_overlay_load(3u);
        if (rc == RSQL_OK) rc = rsql_query_drop_phase();
        return fail(rc, rc == RSQL_OK ? MSG_OK : MSG_STORAGE);
    }
    if (g_rsql_statement.kind == RSQL_STMT_INSERT) {
        rc = rsql_overlay_load(0u);
        if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        rc = rsql_table_find(g_rsql_statement.table_name, &table);
        if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        g_insert_bind_table_page = table.table_page;
        g_insert_bind_row_width = table.row_width;
        g_insert_bind_column_count = table.column_count;
        for (index = 0u; index < table.column_count; ++index) {
            rc = rsql_column_info(table.table_page, index,
                                  &g_rsql_execution.columns[index]);
            if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        }
        /* cc65 can reuse the dynamic column destination's scalar prefix.
         * Publish adjacent execution scalars only after every column call. */
        g_rsql_execution.table_page = g_insert_bind_table_page;
        g_rsql_execution.row_width = g_insert_bind_row_width;
        g_rsql_execution.column_count = g_insert_bind_column_count;
        rc = rsql_query_resolve_insert_enums();
        if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        rc = rsql_overlay_load(3u);
        if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        rc = rsql_query_exec_prepare();
        if (rc != RSQL_OK) return fail(rc, MSG_UNSUPPORTED);
        rc = rsql_journal_begin();
        if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        rc = rsql_overlay_load(0u);
        if (rc == RSQL_OK) rc = rsql_query_materialize_insert();
        if (rc == RSQL_OK) rc = rsql_overlay_load(1u);
        if (rc == RSQL_OK) {
            rc = rsql_row_insert(g_rsql_execution.table_page,
                                 g_rsql_execution.row,
                                 g_rsql_execution.row_width, &row_id);
        }
        if (rc == RSQL_OK) rc = rsql_overlay_load(3u);
        if (rc == RSQL_OK) {
            rc = rsql_index_rebuild_table(g_rsql_execution.table_page);
        }
        rc = rsql_finish_mutation(rc);
        if (rc == RSQL_OK) request->output.affected_rows.bytes[0] = 1u;
        return fail(rc, rc == RSQL_OK ? MSG_OK : MSG_STORAGE);
    }
    if (g_rsql_statement.kind == RSQL_STMT_DELETE ||
        g_rsql_statement.kind == RSQL_STMT_UPDATE) {
        rc = rsql_overlay_load(0u);
        if (rc == RSQL_OK) {
            if (g_rsql_statement.kind == RSQL_STMT_DELETE) {
                rc = rsql_query_bind_delete();
            } else rc = rsql_query_bind_update();
        }
        if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        rc = rsql_overlay_load(1u);
        if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        rc = rsql_journal_begin();
        if (rc != RSQL_OK) return fail(rc, MSG_STORAGE);
        rc = execute_bound_mutation(request);
        if (rc == RSQL_OK) rc = rsql_overlay_load(3u);
        if (rc == RSQL_OK) {
            rc = rsql_index_rebuild_table(g_rsql_cursor.table_page);
        }
        rc = rsql_finish_mutation(rc);
        return fail(rc, rc == RSQL_OK ? MSG_OK : MSG_STORAGE);
    }
    return fail(RSQL_ERR_UNSUPPORTED_SQL, MSG_UNSUPPORTED);
}

const RsqlErrorInfo* rsql_last_error(void) {
    return &g_error;
}

rsql_u8 __fastcall__ rsql_not_implemented(void* request) {
    (void)request;
    return fail(RSQL_ERR_NOT_IMPLEMENTED, MSG_UNSUPPORTED);
}
