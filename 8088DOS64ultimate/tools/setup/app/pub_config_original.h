#ifndef DOS64_INSTALL_CONFIG_H
#define DOS64_INSTALL_CONFIG_H

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

extern unsigned char d64_cfg_input[D64_CFG_BYTES];
extern unsigned char d64_cfg_output[D64_CFG_BYTES];
extern unsigned char d64_path_source[D64_PATH_BYTES];
extern unsigned char d64_path_relative[D64_PATH_BYTES];
extern unsigned char d64_path_output[D64_PATH_BYTES];
extern unsigned char d64_cfg_error;

/* 1 success, 0 failure. Input and previously committed output survive failure. */
unsigned char d64_config_make(void);
unsigned char d64_config_validate(void);
unsigned char d64_path_join(void);
unsigned char d64_path_parent(void);

#endif
