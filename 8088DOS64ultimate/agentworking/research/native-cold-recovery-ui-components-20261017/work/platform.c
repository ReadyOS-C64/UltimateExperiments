#include "platform.h"
#define R(a) (*(volatile ps_u8 *)(a))
extern void ps_guard(void),ps_scan(void);
extern ps_u8 ps_matrix[8];
ps_u8 ps_row,ps_col,ps_color=1,ps_ascii;
ps_u8 ps_key,ps_modifiers,ps_ghost,ps_clock_valid;
ps_u16 ps_ticks;
static ps_u8 armed;
static const ps_u8 normal[64]={
 8,13,PS_RIGHT,PS_F1+6,PS_F1,PS_F1+2,PS_F1+4,PS_DOWN,
 '3','w','a','4','z','s','e',0,
 '5','r','d','6','c','f','t','x',
 '7','y','g','8','b','h','u','v',
 '9','i','j','0','m','k','o','n',
 '+','p','l','-','.',':','@',',',
 '\\','*',';',PS_HOME,0,'=','^','/',
 '1',9,0,'2',' ',0,'q',27
};
static ps_u8 shifted(ps_u8 c) {
 if(c>='a'&&c<='z')return c-32;
 if(c>='1'&&c<='9')return c-16;
 if(c=='0')return '0';
 if(c==8)return PS_DELETE;if(c==9)return 0;
 if(c=='-')return '_';if(c=='@')return '`';if(c=='^')return '~';
 if(c==PS_RIGHT)return PS_LEFT;if(c==PS_DOWN)return PS_UP;
 if(c>=PS_F1&&c<=PS_F1+6)return c+1;
 if(c=='.')return '>';if(c==',')return '<';
 if(c==':')return '[';if(c==';')return ']';
 if(c=='/')return '?';if(c=='\\')return '|';
 return c;
}
ps_u8 ps_glyph(ps_u8 c) {
 if(c>='a'&&c<='z')return c-96;
 if(c=='@')return 0;
 if(c=='[')return 27;if(c==']')return 29;
 if(c=='\\')return '/';if(c=='^')return 30;
 if(c=='_')return '-';if(c=='`')return 39;
 if(c=='{')return 27;if(c=='}')return 29;
 if(c=='|')return '!';if(c=='~')return '-';
 if(c>=32&&c<=90)return c;
 return '?';
}
ps_u8 ps_put(void) {
 ps_u16 at;
 if(ps_row>=25||ps_col>=40||ps_color>15||ps_ascii<32||ps_ascii>126)return 0;
 at=(ps_u16)ps_row*40+ps_col;
 R(0x0400+at)=ps_glyph(ps_ascii);R(0xd800+at)=ps_color;return 1;
}
void ps_clear(void) {
 ps_u16 at;
 for(at=0;at<1000;++at){R(0x0400+at)=32;R(0xd800+at)=ps_color&15;}
}
void ps_init(void) {
 ps_guard();
 /* Bank0 VIC text0400, mixed-case character ROM1800, no sprites/IRQs. */
 R(0xdd02)|=3;R(0xdd00)|=3;
 R(0xd01a)=0;R(0xd019)=15;R(0xd011)=0x1b;R(0xd016)=8;R(0xd018)=0x16;
 R(0xd015)=0;R(0xd020)=6;R(0xd021)=0;
 R(0xdc02)=255;R(0xdc03)=0;R(0xdc00)=255;
 R(0xdd0e)=0;R(0xdd0f)=0x40;
 R(0xdd04)=255;R(0xdd05)=3;R(0xdd06)=255;R(0xdd07)=255;
 R(0xdd0f)=0x51;R(0xdd0e)=0x11;
 ps_ticks=0;ps_clock_valid=0;ps_key=ps_modifiers=ps_ghost=0;armed=1;
 ps_row=ps_col=0;ps_color=1;ps_clear();
}
ps_u8 ps_clock_poll(void) {
 ps_u8 hi,lo,again,n;
 ps_clock_valid=0;
 for(n=0;n<8;++n) {
  hi=R(0xdd07);lo=R(0xdd06);again=R(0xdd07);
  if(hi==again){ps_ticks=~(((ps_u16)hi<<8)|lo);ps_clock_valid=1;return 1;}
 }
 return 0;
}
ps_u8 ps_key_poll(void) {
 ps_u8 row,col,count=0,index=0,mask,other,c,inter;
 ps_scan();ps_key=ps_modifiers=ps_ghost=0;
 if((ps_matrix[1]&128)||(ps_matrix[6]&16))ps_modifiers|=1;
 if(ps_matrix[7]&4)ps_modifiers|=2;
 if(ps_matrix[7]&32)ps_modifiers|=4;
 /* Any sampled rectangle is electrically ambiguous on a diodeless matrix. */
 for(row=0;row<7;++row)for(other=row+1;other<8;++other) {
  inter=ps_matrix[row]&ps_matrix[other];
  if(inter&&(inter&(inter-1)))ps_ghost=1;
 }
 for(row=0;row<8;++row) {
  mask=ps_matrix[row];
  if(row==1)mask&=127;if(row==6)mask&=239;if(row==7)mask&=219;
  for(col=0;col<8;++col)if(mask&(1<<col)){++count;index=row*8+col;}
 }
 if(!count){armed=1;return 0;}
 if(count!=1||ps_ghost){armed=0;return 0;}
 if(!armed)return 0;armed=0;c=normal[index];
 if(!c||ps_modifiers&4)return 0;
 if(ps_modifiers&1)c=shifted(c);
 if(!c)return 0;
 if(ps_modifiers&2) {
  if(c>='a'&&c<='z')c-=96;
  else if(c>='A'&&c<='Z')c-=64;
  else return 0;
 }
 ps_key=c;return 1;
}
