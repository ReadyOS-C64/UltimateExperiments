#include "startup_close.h"
unsigned char sc_abi_begin(void) {return sc_begin(0xa5u);}
unsigned char sc_abi_poll(void) {return sc_poll();}
unsigned char sc_abi_ready(void) {return sc_ready();}
