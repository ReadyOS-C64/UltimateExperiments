#ifndef DOS64_INI_PARSER_H
#define DOS64_INI_PARSER_H
#define NI_CHUNK_BYTES 64u
#define NI_FILE_BYTES 1024u
#define NI_LINE_BYTES 128u
#define NI_IDLE 0u
#define NI_ACTIVE 1u
#define NI_DONE 2u
#define NI_FAILED 3u
#define NI_E_SYNTAX 1u
#define NI_E_UNKNOWN 2u
#define NI_E_VALUE 3u
#define NI_E_SIZE 4u
#define NI_E_ASCII 5u
#define NI_E_DUPLICATE 6u
#define NI_E_STATE 7u
/* Synchronous input: accepted count is captured; input bytes stay stable
 * during feed and may change after return. Set count0..64; zero is not EOF.
 * Exact EOF is caller-owned and represented by explicit finish. No I/O/DMA.
 * Public output is observation only. Use columns()/state()/error() getters.
 * Failed input never publishes, and preserves preceding committed output. */
extern unsigned char ni_input[64], ni_count, ni_output_columns;
unsigned char ni_begin(void);
unsigned char ni_feed(void);
unsigned char ni_finish(void);
unsigned char ni_state(void);
unsigned char ni_error(void);
unsigned int ni_error_line(void);
/* Returns40/80 only for this successfully finished job, otherwise0. */
unsigned char ni_columns(void);
#endif
