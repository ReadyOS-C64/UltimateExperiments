#ifndef DOS64_ACTION_CONTROLLER_H
#define DOS64_ACTION_CONTROLLER_H
typedef unsigned char ac_u8;
typedef unsigned int ac_u16;
typedef unsigned long ac_u32;
#define AC_SAVE 1u
#define AC_SAVE_AS 2u
/* sequence is advisory allocation search hint; result.sequence is selected. */
struct ac_request_t {ac_u8 owner,readonly;ac_u16 sequence;ac_u32 capacity;ac_u8 drive,action;char path[128];};
struct ac_result_t {ac_u8 state,error,phase,worker_error,known_closed,can_resume,committing;ac_u16 sequence;};
extern struct ac_request_t ac_request;
extern struct ac_result_t ac_result;
ac_u8 ac_entry(void);
#endif
