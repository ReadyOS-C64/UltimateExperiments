#ifndef READYFS_HOST_CONIO_H
#define READYFS_HOST_CONIO_H

#define CH_ENTER 13u
#define CH_STOP 3u
#define CH_F1 133u
#define CH_F3 134u
#define CH_F7 136u
#define CH_CURS_UP 145u
#define CH_CURS_DOWN 17u
#define CH_CURS_LEFT 157u
#define CH_CURS_RIGHT 29u
#define CH_HOME 19u
#define CH_INS 148u
#define CH_DEL 20u
#define COLOR_LIGHTBLUE 14u
#define COLOR_WHITE 1u
#define COLOR_RED 2u
#define COLOR_YELLOW 7u
#define COLOR_CYAN 3u
#define COLOR_GRAY1 11u
unsigned char cgetc(void);
unsigned char kbhit(void);
unsigned char wherey(void);
void gotoxy(unsigned char x, unsigned char y);
unsigned char textcolor(unsigned char color);
void clrscr(void);
unsigned char revers(unsigned char enabled);
void cputhex8(unsigned char value);
void cputc(char value);
void cputs(const char *text);

#endif
