#ifndef RSQL_JOURNAL_H
#define RSQL_JOURNAL_H

#include "rsql_types.h"

rsql_u8 rsql_journal_begin(void);
rsql_u8 rsql_journal_commit(void);
rsql_u8 rsql_journal_rollback(void);
rsql_u8 __fastcall__ rsql_finish_mutation(rsql_u8 rc);

/* Target regression hook. 0xFF disables injection; otherwise the selected
 * transaction write returns RSQL_ERR_IO before changing canonical storage. */
void __fastcall__ rsql_journal_test_fail_after(rsql_u8 write_index);
void rsql_journal_test_fail_transaction(rsql_u8 transaction_index,
                                        rsql_u8 write_index);
rsql_u8 rsql_journal_test_write_count(void);

#endif
