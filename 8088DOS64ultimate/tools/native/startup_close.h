#ifndef DOS64_STARTUP_CLOSE_H
#define DOS64_STARTUP_CLOSE_H
#include "bulk_reu.h"
/* Startup-only, same initialized FILES/UCI engine, no prior jobs/UI lease and
 * exclusive target1/2 authority. This is explicit firmware recovery; RAM init
 * is not evidence of firmware closure. Caller validates persistent START
 * settings before A5; SETUP claims capability from its explicit native entry.
 * Update sc_now atomically from coherent elapsed ticks before every poll.
 * One accepted run only. No blind retry and no second transport. */
#define SC_BUSY 1u
#define SC_DONE 2u
#define SC_FAILED 3u
extern br_u16 sc_now;
/* Observation only; private state and closedmask control decisions. */
extern br_u8 sc_state,sc_error,sc_transport,sc_target,sc_closed,sc_cleanup;
br_u8 sc_begin(br_u8 capability); /*1accepted,0refused before command*/
br_u8 sc_poll(void); /*private state after bounded FILES/UCI progress*/
void sc_cancel(void); /*defer through safety CLOSE1/2, then refuse continuation*/
br_u8 sc_ready(void); /*private DONE + both knownclosed + currentquiet/FILES0*/
/* Only strict existing FILES parser00,OK or exact84,NO FILE TO CLOSE can
 * complete an unknown CLOSE with handle0. Other status/protocol/transport
 * failures remain terminal/unknown. error1cancel,2transport,3status,4protocol,
 * 5input; cleanup records later filefailure without replacing first cause. */
#endif
