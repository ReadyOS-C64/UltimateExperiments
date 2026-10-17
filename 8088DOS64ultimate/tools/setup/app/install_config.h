#ifndef DOS64_INSTALL_CONFIG_H
#define DOS64_INSTALL_CONFIG_H

/* UI consumers can explicitly select only canonical path operations. The
 * default full codec and START validate-only build keep their existing ABI. */
#ifndef D64_CONFIG_PATH_ONLY
#define D64_CONFIG_PATH_ONLY 0
#endif

#ifndef D64_CONFIG_INPLACE
#define D64_CONFIG_INPLACE 0
#endif
/* CONFIG-only validation capability. Input is the validated output; strict
 * checks are unchanged. Generic full/START builds retain independent output. */
/* Byte-defined durable CFG and REU handoff body. Never serialize C structs. */
#define D64_CFG_BYTES 576u
#define D64_CFG_HOME 8u
#define D64_CFG_A 136u
#define D64_CFG_B 264u
#define D64_CFG_C 392u
#define D64_CFG_PROFILE 520u
#define D64_CFG_READONLY 524u
#define D64_CFG_PRESENT 525u
#define D64_CFG_A_CRC 528u
#define D64_CFG_B_CRC 532u
#define D64_CFG_BOOT_ABI 536u
#define D64_CFG_REU_BYTES 538u
#define D64_CFG_CRC 572u
#define D64_PATH_BYTES 128u
#define D64_CFG_VERSION 1u

#if !D64_CONFIG_PATH_ONLY
#if D64_CONFIG_INPLACE
extern unsigned char *d64_cfg_input;
#else
extern unsigned char d64_cfg_input[D64_CFG_BYTES];
#endif
#if D64_CONFIG_INPLACE
#define d64_cfg_output d64_cfg_input
unsigned char d64_config_rebase(void);
#else
extern unsigned char d64_cfg_output[D64_CFG_BYTES];
#endif
#endif
extern unsigned char d64_path_source[D64_PATH_BYTES];
extern unsigned char d64_path_relative[D64_PATH_BYTES];
extern unsigned char d64_path_output[D64_PATH_BYTES];
extern unsigned char d64_cfg_error;

/* 1 success, 0 failure. Input and previously committed output survive failure. */
#if !D64_CONFIG_PATH_ONLY
unsigned char d64_config_make(void);
unsigned char d64_config_validate(void);
#endif
unsigned char d64_path_join(void);
unsigned char d64_path_parent(void);

#endif
