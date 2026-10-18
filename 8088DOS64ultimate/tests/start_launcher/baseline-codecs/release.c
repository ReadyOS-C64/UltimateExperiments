#include "release.h"
#include <string.h>
unsigned char d64_release_input[64], d64_release_output[64];
unsigned char d64_release_error;
static unsigned int word(unsigned char n) {
    return (unsigned int)d64_release_input[n] |
        ((unsigned int)d64_release_input[n+1u] << 8);
}
static unsigned long wide(unsigned char n) {
    return (unsigned long)word(n) | ((unsigned long)word(n+2u) << 16);
}
static unsigned long crc(void) {
    unsigned long v=0xffffffffUL;
    unsigned char n,b;
    for(n=0;n<60u;++n) {
        v ^= d64_release_input[n];
        for(b=0;b<8u;++b) v=(v>>1)^((v&1u)?0xedb88320UL:0UL);
    }
    return v^0xffffffffUL;
}
static unsigned char fail(unsigned char n) { d64_release_error=n; return 0; }
static unsigned char span(unsigned long at,unsigned int len,unsigned long size,
                           unsigned int lo,unsigned int hi) {
    unsigned long address;
    if(at<2UL || at>size || len>size-at) return 0;
    address=0x0801UL+at-2UL;
    return address>=lo && address+len<=hi;
}
static unsigned char disjoint(unsigned long a,unsigned int an,
                              unsigned long b,unsigned int bn) {
    return a+an<=b || b+bn<=a;
}
unsigned char d64_release_validate(void) {
    unsigned long size,n,h,f;
    unsigned char i;
    d64_release_error=0;
    if(memcmp(d64_release_input,"D64L",4) ||
       d64_release_input[4]!=1u || d64_release_input[5]!=1u || word(6)!=64u)
        return fail(1);
    if(crc()!=wide(60)) return fail(2);
    if(word(16)!=0x0801u || word(26)!=0x5882u ||
       wide(40)!=0x3e0000UL || wide(44)!=0x3ff000UL || word(48)!=576u ||
       d64_release_input[50]!=32u || d64_release_input[51]!=0x40u ||
       word(52)!=142u || word(54)!=140u) return fail(3);
    for(i=56;i<60u;++i) if(d64_release_input[i]) return fail(3);
    size=wide(8);
    if(size<2UL || size>0xb801UL || (unsigned long)word(18)!=size-2UL)
        return fail(4);
    for(i=20;i<26u;i+=2u)
        if(word(i)<0x0801u || word(i)>=0x4000u ||
           (unsigned long)word(i)>=0x0801UL+size-2UL) return fail(4);
    /* Incoming NMI opcode must actually be inside the staged payload. */
    if(0x5882UL>=0x0801UL+size-2UL) return fail(4);
    n=wide(28); h=wide(32); f=wide(36);
    if(!span(n,142u,size,0x7000u,0x8000u) ||
       !span(h,140u,size,0x7000u,0x8000u) ||
       !span(f,1u,size,0x0801u,0x4000u) ||
       !disjoint(n,142u,h,140u) || !disjoint(n,142u,f,1u) ||
       !disjoint(h,140u,f,1u)) return fail(5);
    /* Release metadata cannot approve replacing a callable entry or vice versa. */
    for(i=20;i<26u;i+=2u)
        if(f==(unsigned long)word(i)-0x0801UL+2UL) return fail(5);
    memcpy(d64_release_output,d64_release_input,64);
    return 1;
}
