#ifndef DOS64_TEMPLATE_LIMITS_H
#define DOS64_TEMPLATE_LIMITS_H
/* Numeric default-OFF profile. Shared native D64S ABI remains unchanged.
 * 20KiB file payload ends57FE, below the5882 NMI guard. */
#ifndef DOS64_SETUP_MNU_56K
#define DOS64_SETUP_MNU_56K 0
#endif
#if DOS64_SETUP_MNU_56K && !DOS64_SETUP_COLD_INVENTORY
#error 56KiB_MNU_requires_cold_inventory
#endif
#ifndef DOS64_START_TEMPLATE_20K
#define DOS64_START_TEMPLATE_20K 0
#endif
#if DOS64_START_TEMPLATE_20K
#define ST_TEMPLATE_BYTES 20480UL
#define ST_TEMPLATE_MAX 0x5001UL
#else
#define ST_TEMPLATE_BYTES 18432UL
#define ST_TEMPLATE_MAX 0x4801UL
#endif
#endif
