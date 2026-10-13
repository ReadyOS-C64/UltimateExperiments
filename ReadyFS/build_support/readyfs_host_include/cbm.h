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
struct cbm_dirent { char name[17]; unsigned int size; unsigned char type, access; };
unsigned char cbm_opendir(unsigned char, unsigned char, ...);
unsigned char cbm_readdir(unsigned char, struct cbm_dirent *);
void cbm_closedir(unsigned char);
void cbm_k_talk(unsigned char);
void cbm_k_tksa(unsigned char);
unsigned char cbm_k_acptr(void);
void cbm_k_untlk(void);
void cbm_k_ciout(unsigned char);
#endif
