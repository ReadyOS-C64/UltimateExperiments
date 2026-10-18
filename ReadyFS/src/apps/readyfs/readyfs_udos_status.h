#ifndef READYFS_UDOS_STATUS_H
#define READYFS_UDOS_STATUS_H
/* Numeric bytes are deliberate. cc65 translates even \xNN string escapes
 * through its PETSCII character map; the UltimateDOS status wire is ASCII. */
#define RF_UDOS_EMPTY_BYTES {48,49,44,68,73,82,69,67,84,79,82,89,32,69,77,80,84,89,0}
#define RF_UDOS_MISSING_BYTES {70,73,76,69,32,68,79,69,83,78,39,84,32,69,88,73,83,84,0}
#endif
