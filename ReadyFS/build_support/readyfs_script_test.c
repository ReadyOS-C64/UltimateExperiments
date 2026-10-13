#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include "src/apps/readyfs/readyfs_script.h"
#include "src/apps/readyfs/readyfs_reu.h"
#include "src/apps/readyfs/readyfs_result.h"

static unsigned char batch_ram[65536], script_ram[65536], session_ram[65536];
static char output[32768];
static unsigned int out_used;
static unsigned char stop_key;
static char line[256];
static char *argv[12];
static ReadyFsBatchCall call;
static unsigned int checks;
#define CHECK(expr) do { ++checks; assert(expr); } while (0)
unsigned char readyfs_same_word(const char *a, const char *b) {
    while (*a && *b) if (tolower((unsigned char)*a++) != tolower((unsigned char)*b++)) return 0u;
    return *a == *b;
}
void cputs(const char *s) { size_t n = strlen(s); assert(out_used+n<sizeof(output)); memcpy(output+out_used,s,n+1);out_used+=(unsigned int)n; }
void clrscr(void) {}
void cputc(char c) { char s[2] = {c,0};cputs(s); }
unsigned char kbhit(void) { return stop_key; }
unsigned char cgetc(void) { stop_key=0;return 3u; }
#define DMA_PAIR(name, ram) \
unsigned char readyfs_reu_##name##_store(unsigned int off,const void *p,unsigned int n) { assert(off+n<=sizeof(ram));memcpy(ram+off,p,n);return 1u; } \
unsigned char readyfs_reu_##name##_fetch(unsigned int off,void *p,unsigned int n) { assert(off+n<=sizeof(ram));memcpy(p,ram+off,n);return 1u; }
DMA_PAIR(batch,batch_ram)
DMA_PAIR(script,script_ram)
DMA_PAIR(session,session_ram)

static void reset_output(void) { output[0]=0;out_used=0; }
static void init(void) {
    memset(&call,0,sizeof(call));call.operation=RF_ENV_INIT;
    CHECK(readyfs_environment(&call));
    reset_output();
}
static void prepare(const char *text, unsigned char rc, unsigned char positional) {
    strcpy(line,text);memset(&call,0,sizeof(call));
    call.operation=RF_ENV_EXPAND;call.buffer=line;call.capacity=sizeof(line);call.args=argv;
    call.rc=rc;call.finish=positional;
    CHECK(readyfs_expand(&call));
}
static void command(const char *text) {
    prepare(text,0u,0u);CHECK(call.action==RF_BATCH_COMMAND);
    call.operation=RF_ENV_COMMAND;CHECK(readyfs_environment(&call));
}
static ReadyFsVariable variable(unsigned char i) {
    ReadyFsVariable v;memcpy(&v,script_ram+RF_SCRIPT_VARS_OFF+(unsigned int)i*RF_SCRIPT_RECORD_BYTES,sizeof(v));return v;
}
static unsigned char value_is(const char *name,const char *value) {
    unsigned char i;ReadyFsVariable v;
    for(i=0;i<RF_SCRIPT_VARS;++i) { v=variable(i);if(readyfs_same_word(name,v.name)) return strcmp(value,v.value)==0; }
    return 0u;
}
static unsigned char run(const char *script) {
    unsigned int guard=0;
    ReadyFsBatchState state;
    size_t n=strlen(script);
    memcpy(batch_ram+RF_REU_BATCH_DATA_OFF,script,n);
    memset(&call,0,sizeof(call));call.operation=RF_BATCH_INIT;call.size=(unsigned int)n;
    CHECK(readyfs_batch_dispatch(&call));
    while(++guard<11000u) {
        call.operation=RF_BATCH_READ;call.buffer=line;call.capacity=sizeof(line);call.args=argv;
        CHECK(readyfs_batch_dispatch(&call));
        if(call.action==RF_BATCH_DONE) break;
        call.operation=RF_ENV_EXPAND;call.finish=1u;CHECK(readyfs_expand(&call));
        if(call.action==RF_BATCH_ERROR) { call.operation=RF_BATCH_ACK;call.finish=1u;CHECK(readyfs_batch_dispatch(&call));continue; }
        if(call.action==RF_BATCH_SKIP) continue;
        call.operation=RF_BATCH_FLOW;CHECK(readyfs_flow(&call));
        if(call.action==RF_BATCH_EXISTS) {
            unsigned char exists=strcmp(call.test,"8:/present")==0;
            if(exists==call.finish) continue;
            CHECK(readyfs_flow(&call));
        }
        if(call.action==RF_BATCH_SKIP) continue;
        call.operation=RF_ENV_COMMAND;call.rc=0u;CHECK(readyfs_environment(&call));
        if(call.action==RF_BATCH_SKIP) {call.operation=RF_BATCH_ACK;call.finish=0u;CHECK(readyfs_batch_dispatch(&call));continue;}
        call.operation=RF_BATCH_EVAL;CHECK(readyfs_batch_dispatch(&call));
        if(call.action==RF_BATCH_SKIP) continue;
        call.rc=readyfs_same_word(argv[0],"fail")?8u:0u;
        call.operation=RF_BATCH_ACK;call.finish=0u;CHECK(readyfs_batch_dispatch(&call));
    }
    CHECK(guard<11000u);
    memcpy(&state,batch_ram+RF_REU_BATCH_STATE_OFF,sizeof(state));
    return state.last_rc;
}
static void variable_tests(void) {
    ReadyFsVariable v;
    init();command("SET SOURCE=8:/work");CHECK(value_is("source","8:/work"));
    v=variable(0);CHECK(!v.persistent);
    command("SET /P TARGET=9:/backup");v=variable(1);CHECK(v.persistent);
    prepare("COPY %SOURCE% %TARGET%",0u,0u);CHECK(call.argc==3u);CHECK(!strcmp(argv[1],"8:/work"));CHECK(!strcmp(argv[2],"9:/backup"));
    prepare("ECHO \"hello %SOURCE%\" %% %MISSING%",0u,0u);CHECK(call.argc==3u);CHECK(!strcmp(argv[1],"hello 8:/work"));CHECK(!strcmp(argv[2],"%"));
    prepare("ECHO %ERRORLEVEL%",105u,0u);CHECK(!strcmp(argv[1],"105"));
    command("SET TARGET=temporary");v=variable(1);CHECK(!v.persistent);
    command("SET SOURCE=");CHECK(!value_is("source","8:/work"));
    command("SET \"GREETING=hello there\"");CHECK(value_is("greeting","hello there"));
    prepare("ECHO \"unterminated",0u,0u);CHECK(call.action==RF_BATCH_ERROR);
    prepare("ECHO %unterminated",0u,0u);CHECK(call.action==RF_BATCH_ERROR);
    prepare("ECHO 1 2 3 4 5 6 7 8 9 10 11 12",0u,0u);CHECK(call.action==RF_BATCH_ERROR);
    prepare("",8u,0u);CHECK(call.action==RF_BATCH_SKIP);CHECK(call.rc==8u);
    prepare("REM %broken \"",0u,0u);CHECK(call.action==RF_BATCH_SKIP);
    prepare("# %broken \"",8u,0u);CHECK(call.action==RF_BATCH_SKIP);CHECK(call.rc==8u);
    command("SET /A N=65535+1");CHECK(value_is("N","0"));
    command("SET /P /A N=N+7");CHECK(value_is("N","7"));
    command("SET /A N=bad+1");CHECK(value_is("N","1")); /* undefined operands are zero */
    command("SET /A N=65536");CHECK(call.rc==RF_RESULT_USAGE);CHECK(value_is("N","1"));
    command("SET ERRORLEVEL=9");CHECK(call.rc==RF_RESULT_USAGE);
    { char text[180];memset(text,'x',sizeof(text));memcpy(text,"SET LONG=",9);text[9+128]=0;command(text);CHECK(call.rc==RF_RESULT_USAGE); }
    command("SET LONG=abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz");
    prepare("ECHO %LONG%%LONG%%LONG%",0u,0u);CHECK(call.action==RF_BATCH_ERROR);
    prepare("RUN SCRIPT \"first arg\" second",0u,0u);call.operation=RF_ENV_ARGUMENTS;CHECK(readyfs_expand(&call));
    prepare("ECHO %0 %1 %2 %9",0u,1u);CHECK(call.argc==5u);CHECK(!strcmp(argv[1],"SCRIPT"));CHECK(!strcmp(argv[2],"first"));CHECK(!strcmp(argv[3],"arg")); /* unquoted argument expansion splits */
    prepare("ECHO \"%1\"",0u,1u);CHECK(call.argc==2u);CHECK(!strcmp(argv[1],"first arg"));
}
static void flow_tests(void) {
    init();
    CHECK(run("SET NAME=world\nIF \"%NAME%\"==\"world\" GOTO good\nECHO BAD\n:good\nCALL :sub\nECHO AFTER\nGOTO :EOF\n:sub\nECHO HELLO %NAME%\nEXIT /B\n")==0u);
    CHECK(strstr(output,"HELLO world")!=0);CHECK(strstr(output,"AFTER")!=0);CHECK(strstr(output,"BAD")==0);
    reset_output();CHECK(run("ONERROR CONTINUE\nFAIL\nIF ERRORLEVEL 8 ECHO CAUGHT\nIF NOT DEFINED ABSENT ECHO UNDEFINED\nIF 3 LSS 4 ECHO NUMERIC\nIF EXIST 8:/present ECHO EXISTS\nIF NOT EXIST 8:/absent ECHO MISSING\nIF a==b ECHO BAD\n")==0u);
    CHECK(strstr(output,"CAUGHT")!=0);CHECK(strstr(output,"UNDEFINED")!=0);CHECK(strstr(output,"NUMERIC")!=0);CHECK(strstr(output,"EXISTS")!=0);CHECK(strstr(output,"MISSING")!=0);CHECK(strstr(output,"BAD")==0);
    reset_output();CHECK(run("SET /A N=0\n:loop\nSET /A N=N+1\nIF %N% LSS 3 GOTO loop\nECHO COUNT %N%\n")==0u);CHECK(strstr(output,"COUNT 3")!=0);
    CHECK(run("GOTO missing\nECHO BAD\n")==RF_RESULT_USAGE);
    CHECK(run("CALL :again\nGOTO :EOF\n:again\nCALL :again\nEXIT /B\n")==RF_RESULT_USAGE);
    CHECK(run("EXIT /B 9\nECHO BAD\n")==9u);
    CHECK(run("IF ERRORLEVEL nonsense ECHO BAD\n")==RF_RESULT_USAGE);
    reset_output();CHECK(run("FAIL\nECHO BAD\n")==8u);CHECK(strstr(output,"BAD")==0);
    reset_output();CHECK(run("# comment\nONERROR STOP\nOK\nEXPECT RC 0\n")==0u);CHECK(strstr(output,"expect rc ok")!=0);
    reset_output();stop_key=1u;CHECK(run("ECHO BAD\n")==RF_RESULT_INTERACTION);CHECK(strstr(output,"BAD")==0);
    { char too_long[300];memset(too_long,'X',sizeof(too_long));too_long[sizeof(too_long)-1]=0;CHECK(run(too_long)==RF_RESULT_INTERACTION); }
    call.operation=RF_BATCH_INIT;call.size=RF_REU_BATCH_DATA_BYTES+1u;CHECK(!readyfs_batch_dispatch(&call));
    reset_output();CHECK(run(":again\nGOTO again\n")==RF_RESULT_INTERACTION);CHECK(strstr(output,"step limit")!=0);
}
static void persistence_tests(void) {
    unsigned char saved[RF_SCRIPT_TABLE_BYTES];
    ReadyFsVariable staged;
    unsigned char i;
    init();command("SET SESSION=keep");command("SET /P SAVED=original");
    for(i=0;i<RF_SCRIPT_VARS;++i) {call.operation=RF_ENV_EXPORT;call.size=i;call.buffer=(char *)saved+(unsigned int)i*RF_SCRIPT_RECORD_BYTES;CHECK(readyfs_environment(&call));}
    CHECK(!saved[0]);memcpy(&staged,saved+RF_SCRIPT_RECORD_BYTES,sizeof(staged));CHECK(!strcmp(staged.name,"SAVED"));
    command("SET /P SAVED=changed");command("SET /P LATER=remove");
    for(i=0;i<RF_SCRIPT_VARS;++i) {call.operation=RF_ENV_STAGE;call.size=i;call.buffer=(char *)saved+(unsigned int)i*RF_SCRIPT_RECORD_BYTES;call.rc=0;CHECK(readyfs_environment(&call));CHECK(!call.rc);}
    call.operation=RF_ENV_MERGE;call.rc=0;CHECK(readyfs_environment(&call));CHECK(!call.rc);CHECK(value_is("SAVED","changed"));
    call.operation=RF_ENV_COMMIT;CHECK(readyfs_environment(&call));CHECK(value_is("SESSION","keep"));CHECK(value_is("SAVED","original"));CHECK(!value_is("LATER","remove"));
    init(); /* Fresh session restores only persistent records. */
    for(i=0;i<RF_SCRIPT_VARS;++i) {call.operation=RF_ENV_STAGE;call.size=i;call.buffer=(char *)saved+(unsigned int)i*RF_SCRIPT_RECORD_BYTES;call.rc=0;CHECK(readyfs_environment(&call));}
    call.operation=RF_ENV_MERGE;CHECK(readyfs_environment(&call));call.operation=RF_ENV_COMMIT;CHECK(readyfs_environment(&call));CHECK(value_is("SAVED","original"));CHECK(!value_is("SESSION","keep"));
    memset(&staged,'x',sizeof(staged));call.operation=RF_ENV_STAGE;call.size=0;call.buffer=(char *)&staged;call.rc=0;CHECK(readyfs_environment(&call));CHECK(call.rc==RF_RESULT_USAGE);CHECK(value_is("SAVED","original"));
    /* Duplicate saved names are rejected before replacing any live value. */
    memset(&staged,0,sizeof(staged));strcpy(staged.name,"DUP");strcpy(staged.value,"first");staged.persistent=1u;
    for(i=0;i<RF_SCRIPT_VARS;++i) {
        call.operation=RF_ENV_STAGE;call.size=i;call.buffer=(char *)&staged;call.rc=0;
        CHECK(readyfs_environment(&call));CHECK(!call.rc);
        if(i==1u) memset(&staged,0,sizeof(staged));
    }
    call.operation=RF_ENV_MERGE;call.rc=0;CHECK(readyfs_environment(&call));CHECK(call.rc==RF_RESULT_USAGE);CHECK(value_is("SAVED","original"));
    /* A full session plus an unrelated saved name cannot overflow the table. */
    init();
    for(i=0;i<RF_SCRIPT_VARS;++i) { char assignment[40];snprintf(assignment,sizeof(assignment),"SET V%u=session",i);command(assignment);CHECK(!call.rc); }
    command("SET EXTRA=overflow");CHECK(call.rc==RF_RESULT_CONFLICT);CHECK(value_is("V15","session"));
    memset(&staged,0,sizeof(staged));strcpy(staged.name,"NEW");strcpy(staged.value,"saved");staged.persistent=1u;
    for(i=0;i<RF_SCRIPT_VARS;++i) {call.operation=RF_ENV_STAGE;call.size=i;call.buffer=(char *)&staged;call.rc=0;CHECK(readyfs_environment(&call));CHECK(!call.rc);memset(&staged,0,sizeof(staged));}
    call.operation=RF_ENV_MERGE;call.rc=0;CHECK(readyfs_environment(&call));CHECK(call.rc==RF_RESULT_CONFLICT);CHECK(value_is("V0","session"));CHECK(!value_is("NEW","saved"));

}
/* Config sidecar I/O is tested below using a real serialized byte stream. */
static unsigned char config_file[6000];
static unsigned int config_size, config_cursor;
static unsigned char config_closed;
unsigned char readyfs_config_io(ReadyFsBatchCall *c) {
    if(c->operation==RF_CONFIG_READ) {if(config_cursor+c->size>config_size)return 0u;memcpy(c->buffer,config_file+config_cursor,c->size);config_cursor+=c->size;return 1u;}
    if(c->operation==RF_CONFIG_EOF)return config_cursor==config_size;
    if(c->operation==RF_CONFIG_CLOSE){config_closed=1u;return 1u;}
    return readyfs_environment(c);
}
unsigned char readyfs_overlay_resume_config(void){return 1u;}
static void config_tests(void) {
    char cwd[256]="8:/saved", scratch[273];
    unsigned char i;
    init();command("SET PRIVATE=secret");command("SET /P SAVED=original");
    memset(session_ram,0,sizeof(session_ram));
    strcpy((char *)session_ram,"WORK");strcpy((char *)session_ram+17,"8:/work");
    config_size=0;
    for(i=0;i<26u;++i){call.operation=RF_CONFIG_EXPORT;call.size=i;call.buffer=scratch;call.test=cwd;CHECK(readyfs_config(&call));memcpy(config_file+config_size,scratch,call.size);config_size+=call.size;}
    CHECK(config_size==8u+256u+8u*273u+16u*146u);CHECK(!memcmp(config_file,"RFC2",4));
    init();strcpy(cwd,"9:/current");memset(session_ram,0,8u*273u);config_cursor=0;config_closed=0;
    call.operation=RF_CONFIG_LOAD;call.buffer=scratch;call.test=cwd;CHECK(readyfs_config(&call));CHECK(!call.rc);CHECK(config_closed);CHECK(!strcmp(cwd,"8:/saved"));CHECK(!strcmp((char *)session_ram,"WORK"));CHECK(value_is("SAVED","original"));CHECK(!value_is("PRIVATE","secret"));
    strcpy(cwd,"9:/untouched");command("SET /P SAVED=current");config_file[config_size-1]=2u;config_cursor=0;
    call.operation=RF_CONFIG_LOAD;call.buffer=scratch;call.test=cwd;CHECK(readyfs_config(&call));CHECK(call.rc);CHECK(!strcmp(cwd,"9:/untouched"));CHECK(value_is("SAVED","current"));
    config_file[config_size-1]=0;--config_size;config_cursor=0;call.operation=RF_CONFIG_LOAD;CHECK(readyfs_config(&call));CHECK(call.rc);CHECK(!strcmp(cwd,"9:/untouched"));
    config_file[3]='1';config_size=8u+256u+8u*273u;config_cursor=0;call.operation=RF_CONFIG_LOAD;CHECK(readyfs_config(&call));CHECK(!call.rc);CHECK(value_is("SAVED","current"));
    config_file[4]=9u;config_cursor=0;strcpy(cwd,"9:/still");call.operation=RF_CONFIG_LOAD;CHECK(readyfs_config(&call));CHECK(call.rc);CHECK(!strcmp(cwd,"9:/still"));
}
int main(void) {
    CHECK(sizeof(ReadyFsVariable)==RF_SCRIPT_RECORD_BYTES);
    variable_tests();flow_tests();persistence_tests();config_tests();
    printf("ReadyFS scripting: %u checks passed\n",checks);return 0;
}
