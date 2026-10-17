#if D64_START_OPTIONS
#pragma code-name ("PRELAUNCH")
#pragma rodata-name ("PRELAUNCH_RO")
#endif
#include "ini_parser.h"
unsigned char ni_input[64], ni_count, ni_output_columns;
static unsigned char phase, first_error, section, seen, staged, committed;
static unsigned char used, swallow_lf;
static unsigned int bytes, line_number, error_line;
static unsigned char line[128];

static unsigned char fail(unsigned char code) {
    if (!first_error) { first_error=code; error_line=line_number; }
    phase=NI_FAILED;
    return 0;
}
static unsigned char space(unsigned char c) { return c==' ' || c=='\t'; }
static unsigned char fold(unsigned char c) {
    if (c>='A' && c<='Z') c+=32;
    return c;
}
static unsigned char equal(unsigned char start,unsigned char length,const char *word) {
    unsigned char i=0;
    while(i<length && word[i]) {
        if(fold(line[start+i])!=(unsigned char)word[i]) return 0;
        ++i;
    }
    return i==length && !word[i];
}
static unsigned char parse_line(void) {
    unsigned char start=0,end=used,at,key_end,value,mask;
    /* ASCII was checked before buffering, including bytes inside comments. */
    for(at=0;at<end;++at) if(line[at]=='#'||line[at]==';') { end=at;break; }
    while(start<end && space(line[start])) ++start;
    while(end>start && space(line[end-1])) --end;
    if(start==end) return 1;
    if(line[start]=='[') {
        if(line[end-1]!=']') return fail(NI_E_SYNTAX);
        ++start;--end;
        while(start<end && space(line[start])) ++start;
        while(end>start && space(line[end-1])) --end;
        if(!equal(start,end-start,"emulator")) return fail(NI_E_UNKNOWN);
        section=1;return 1;
    }
    if(!section) return fail(NI_E_SYNTAX);
    at=start;
    while(at<end && line[at]!='=') ++at;
    if(at==end) return fail(NI_E_SYNTAX);
    key_end=at;
    while(key_end>start && space(line[key_end-1])) --key_end;
    value=at+1;
    while(value<end && space(line[value])) ++value;
    if(equal(start,key_end-start,"initial_columns")) mask=1;
    else if(equal(start,key_end-start,"schema")) mask=2;
    else return fail(NI_E_UNKNOWN);
    if(seen&mask) return fail(NI_E_DUPLICATE);
    if(mask==1) {
        if(end-value!=2 || line[value+1]!='0' ||
           (line[value]!='4' && line[value]!='8')) return fail(NI_E_VALUE);
        staged=line[value]=='4'?40:80;
    } else if(end-value!=1 || line[value]!='1') return fail(NI_E_VALUE);
    seen|=mask;
    return 1;
}
unsigned char ni_begin(void) {
    if(phase==NI_ACTIVE) return 0;
    phase=NI_ACTIVE;first_error=0;section=0;seen=0;staged=80;
    used=0;swallow_lf=0;bytes=0;line_number=1;error_line=0;
    return 1;
}
unsigned char ni_feed(void) {
    unsigned char i,c,count;
    if(phase!=NI_ACTIVE) return fail(NI_E_STATE);
    count=ni_count;
    if(count>NI_CHUNK_BYTES) return fail(NI_E_SIZE);
    for(i=0;i<count;++i) {
        if(bytes==NI_FILE_BYTES) return fail(NI_E_SIZE);
        ++bytes;c=ni_input[i];
        if(c!='\t' && c!='\r' && c!='\n' && (c<32 || c>126)) return fail(NI_E_ASCII);
        if(swallow_lf) { swallow_lf=0;if(c=='\n') continue; }
        if(c=='\r'||c=='\n') {
            if(!parse_line()) return 0;
            used=0;++line_number;swallow_lf=c=='\r';
        } else {
            if(used==NI_LINE_BYTES) return fail(NI_E_SIZE);
            line[used++]=c;
        }
    }
    return 1;
}
unsigned char ni_finish(void) {
    if(phase!=NI_ACTIVE) return fail(NI_E_STATE);
    if(!parse_line()) return 0;
    committed=staged;ni_output_columns=committed;phase=NI_DONE;
    return 1;
}
unsigned char ni_state(void) { return phase; }
unsigned char ni_error(void) { return first_error; }
unsigned int ni_error_line(void) { return error_line; }
unsigned char ni_columns(void) { return phase==NI_DONE?committed:0; }
