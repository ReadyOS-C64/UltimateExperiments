#ifndef READYFS_RESULT_H
#define READYFS_RESULT_H

/* Stable command/batch result ABI. The original 0..3 dispatch values stay
 * compatible while handlers migrate to typed filesystem outcomes. */
#define RF_RESULT_OK            0u
#define RF_RESULT_UNKNOWN       1u
#define RF_RESULT_UNAVAILABLE   2u
#define RF_RESULT_INTERACTION   3u
#define RF_RESULT_USAGE         4u
#define RF_RESULT_NOT_FOUND     5u
#define RF_RESULT_CONFLICT      6u
#define RF_RESULT_UNSUPPORTED   7u
#define RF_RESULT_IO            8u
#define RF_RESULT_VERIFY        9u
#define RF_RESULT_PARTIAL      10u
#define RF_RESULT_INTERNAL     11u

#endif
