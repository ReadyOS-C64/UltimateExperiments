#include "validator_crc.h"
unsigned long d64_fast_crc(const unsigned char *p,unsigned int n) {
    if(!c32_init()){c32_error=1u;return 0UL;}
    c32_address=(unsigned int)p;c32_length=n;
    if(!c32_update() || !c32_finish()) {
        if(!c32_error)c32_error=2u;
        return 0UL;
    }
    return c32_crc;
}
