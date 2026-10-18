#ifndef DOS64_PUBLISH_CONSTRUCT_H
#define DOS64_PUBLISH_CONSTRUCT_H
/* Profile-only typed lifetime: codec prepare finishes before ST capture.
 * Valid/error/one-shot state remains outside this byte-storage union. */
union pub_construct_t {unsigned char prepared[576];struct {unsigned char desc[64],home[128],buffer[256];unsigned int base;unsigned long size,control,checksum,raw;} st;};
extern union pub_construct_t pub_construct;
extern unsigned char pub_construct_owner; /* INTERNAL0free1codec2template3failed */
#endif
