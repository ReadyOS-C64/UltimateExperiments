/* Read-only network reachability probe, using the production UCI barrier. */
#include "readyfs_uci.h"
#include <conio.h>
#include <string.h>
static unsigned char data[512],stat[96],cmd[96];
static ReadyFsUciTransfer xfer;
static void call(unsigned int n) {
    unsigned int i;
    xfer.data=data;xfer.data_cap=sizeof(data);xfer.stat=stat;xfer.stat_cap=sizeof(stat);xfer.on_block=0;
    cputs(readyfs_uci_command(cmd,n,&xfer)?"ok ":"transport ");
    cputhex8(xfer.flags);cputc(' ');
    for(i=0;i<xfer.stat_len;++i)cputc(stat[i]);cputs("\r\n");
    for(i=0;i<xfer.data_len && i<12;++i){cputhex8(data[i]);cputc(' ');}cputs("\r\n");
}
int main(void) {
    clrscr();cputs("readyfs mount query probe\r\n");
    cputc(readyfs_uci_detect()?'1':'0');cputs("\r\n");
    cmd[0]=3;cmd[1]=5;cmd[2]=0;call(3);
    cputs("self tcp 10.0.0.79:80\r\n");
    cmd[0]=3;cmd[1]=7;cmd[2]=80;cmd[3]=0;strcpy((char *)cmd+4,"10.0.0.79");call(14);
    if(xfer.data_len==1 && stat[0]=='0' && stat[1]=='0') {cmd[0]=3;cmd[1]=9;cmd[2]=data[0];call(3);}
    cputs("probe done\r\n");while(1);return 0;
}
