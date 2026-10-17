#ifndef DOS64_MEDIA_BIND_H
#define DOS64_MEDIA_BIND_H
/* Caller owns authentic broker/exclusive post-WIRE job. No call/frame into
 * retired WIRE/PLAN. Initialized phase; one-shot failure never rearmed. */
unsigned char mb_bind(void),mb_state(void),mb_error(void);
extern unsigned char mb_cancel_seen; /* observation: lateStop deferred */
#endif
