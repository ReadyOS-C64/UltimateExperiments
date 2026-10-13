#ifndef READYFS_HOST_CBM_H
#define READYFS_HOST_CBM_H
unsigned char cbm_open(unsigned char, unsigned char, unsigned char, const char *);
int cbm_read(unsigned char, void *, unsigned int);
int cbm_write(unsigned char, const void *, unsigned int);
void cbm_close(unsigned char);
void cbm_k_clrch(void);
void cbm_k_listen(unsigned char);
void cbm_k_second(unsigned char);
unsigned char cbm_k_readst(void);
void cbm_k_unlsn(void);
#endif
