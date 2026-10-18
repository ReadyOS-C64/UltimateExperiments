#ifndef DOS64_BULK_REU_H
#define DOS64_BULK_REU_H
/* cc65 C ABI; fixed byte layout, little endian. Independent native code.
 * Single exclusive UCI owner; C caller owns IRQs, D=0 and software stack. All C code/state/software stack must be writable
 * RAM visible with $01=$35, outside IO; caller supplies elapsed monotonic ticks.
 * Never call init while active/open; never mutate REU source or DMA concurrently.
 * br_now16 must be updated atomically; no IRQ may change it mid-call.
 * All file OPENs require ownerA5 and exact root/basename capability. Readonly
 * OPEN captures immutable mode1 and refuses SAVE even if public mode changes.
 * Config root is an externally authorized owned canonical absolute ASCII directory, not proof that
 * an on-disk OWNER file exists. Root/target/capacity immutable while handle open.
 */
typedef unsigned char br_u8;
typedef unsigned int br_u16;
typedef unsigned long br_u32;
#define BR_OPEN 2
#define BR_CLOSE 3
#define BR_READ 4 /* CPU reply1..512B in uci_data; setup HIGH_CODE must be installed */
#define BR_SEEK 6
#define BR_INFO 7
#define BR_LOAD 0x21
#define BR_SAVE 0x22
#define BR_IDLE 0
#define BR_BUSY 1
#define BR_DONE 2
#define BR_FAILED 3
#define BR_INPUT 1
#define BR_TRANSPORT 2
#define BR_STATUS 3
#define BR_PROTOCOL 4
#define BR_COUNT 5
#define BR_CANCEL 6
/* Config offsets owner0,target1,capacity2..5,root6..133 (128 bytes). */
struct br_config_t { br_u8 owner,target; br_u32 capacity; char root[128]; };
/* Request offsets op0,mode1,offset2..5,address6..9,length10..13,path14..141. */
struct br_request_t { br_u8 op,mode; br_u32 offset,address,length; char path[128]; };
/* Result offsets state0,error1,transport2,handle3,known4,uncertain5,rejected6,
 * op7,actual8..11,size12..15,accepted16..17. DONE is not persistence proof.
 * handle0 closed,1 known-open,2 uncertain. Error is first reason, retained.
 * rejected pertains only latest rejected start; no wire/result mutation.
 */
struct br_result_t { br_u8 state,error,transport,handle,known,uncertain,rejected,op; br_u32 actual,size; br_u16 accepted; };
extern struct br_config_t br_config;
extern struct br_request_t br_request;
extern struct br_result_t br_result;
extern br_u16 br_now;
br_u8 br_ui_acquire(void); /*1claims directory-only raw UCI; no openhandle*/
br_u8 br_ui_release(void); /*1releases only at verified quiet transport*/
void br_init(void);                  /* startup only, config remains defaultOFF */
br_u8 br_start(void);                /* 1 accepted,0 rejected; snapshots inputs */
void br_poll(void);
void br_cancel(void);                /* once accepted, bounded transport ABORT */
/* Existing UCI timeout/recovery_timeout defaults128ticks; set before starting,
 * duration1..7fff and poll less than8000ticks apart. Tick unit caller-owned. */
#endif
