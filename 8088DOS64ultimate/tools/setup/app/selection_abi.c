#include "setup_select.h"
br_u8 ss_test_owner,ss_test_value; br_u16 ss_test_timeout;
void ss_test_begin(void){ss_test_value=ss_begin(ss_test_owner,ss_test_timeout);}
