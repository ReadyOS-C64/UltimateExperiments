#include "readyfs_present.h"
#include "readyfs_plan.h"
#include "readyfs_exec.h"
#include "readyfs_reu.h"
#include "readyfs_console.h"
#include <conio.h>
#include <string.h>


static void print_u32(unsigned int high, unsigned int low) {
    unsigned char digits[10];
    unsigned char bit;
    unsigned char i;
    unsigned char carry;
    unsigned char next;
    unsigned char started;

    memset(digits, 0, sizeof(digits));
    for (bit = 0u; bit < 32u; ++bit) {
        carry = (unsigned char)((high & 0x8000u) != 0u);
        high = (unsigned int)((high << 1u) | (low >> 15u));
        low <<= 1u;
        for (i = 10u; i != 0u; --i) {
            next = (unsigned char)(digits[i - 1u] * 2u + carry);
            digits[i - 1u] = (unsigned char)(next % 10u);
            carry = (unsigned char)(next / 10u);
        }
    }
    started = 0u;
    for (i = 0u; i < 10u; ++i) {
        if (digits[i] != 0u || i == 9u) started = 1u;
        if (started) cputc((char)('0' + digits[i]));
    }
}

unsigned char readyfs_transfer_present(ReadyFsUtilityCall *call) {
    const char *name;
    if ((call->argc & 3u) == 0u) {
        cputs(RF_SUMMARY);
        cputs(call->argc & 8u ? "moving " : "copying ");
        cputs(call->buffer); cputs("\r\n");
        return 1u;
    }
    name = strrchr(call->buffer, '/');
    if (name) ++name;
    else name = call->buffer;
    if ((call->argc & 3u) == 2u) cputs(RF_ERROR "copy failed ");
    else {
        cputs(RF_SUMMARY);
        cputs(call->argc & 8u ? "verify: unavailable for tape\r\n" :
              call->argc & 4u ? "verify: skipped\r\n" : "verify: identical\r\n");
        cputs(RF_SUMMARY "copied ");
    }
    cputs(name); cputs(": ");
    print_u32(call->value_high, call->value_low);
    cputs(call->argc & 8u ? " bytes tape\r\n" : " bytes\r\n");
    return 1u;
}
