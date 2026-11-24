# C64 LLM v0.7 technical details

## Model and resident 6510 engine

Both release models use four causal transformer layers with 96 channels, four attention heads of width 24, a 256-channel ReLU feed-forward block, and a 97-token character vocabulary. The input embedding also serves as the output matrix. The learned position budget covers the prompt, delimiter, and generated answer.

| Model | Image layout | Learned positions | REU slot |
| --- | --- | ---: | --- |
| [WollyMonjac’s Tiny 2.1](https://github.com/WollyMonjac/Tiny-2.1) | T64M v3, 380,995 bytes | 128 | `$000000` |
| C64PROGINFO | T64M v4, 390,499 bytes | 224 | `$100000` |

The resident 6502/6510 engine streams weight and cache tiles through the REU and uses the same code for all layers. **F1** selects Tiny 2.1 and **F3** selects C64PROGINFO. For the selected model, the PRG checks the expected image CRC32 in REU, then opens and validates the header and matrix directory. If the copy is missing or invalid, Ultimate DOS loads the matching file into the selected slot before checking it again. A failed switch leaves the previous model available. A successful switch resets the active context.

## Fixed-point arithmetic

Residuals, normalization inputs and logits use signed Q16.16. Each dense projection packs activations into signed 16-bit integers with a shared right-shift exponent chosen from the largest magnitude. Weight rows retain their original signed int8 values. Each row’s scale becomes Q0.24 on conversion. The engine accumulates signed products before applying the row scale and shared exponent, rounding to nearest with ties away from zero.

RMS normalization sums squares in a widened accumulator before taking an integer square root and applying Q4.12 gains. The fixed-point path retains fractional guard bits in the square root. ReLU clamps negative feed-forward activations to zero. Greedy decoding selects the largest logit after row rescaling, and ties keep the first vocabulary entry.

## Lookup tables and packed weights

The compact multiplier uses the quarter-square identity to replace byte products with table lookups and subtraction. The v3 model layout keeps these compact kernels for F2 and the embedding paths. Q, K, V and F1 instead use group-eight subset-sum tables, while O uses groups of four.

For a group of eight packed activations, the 6510 computes all 256 subset sums and stores each in three bytes. Offline packing transposes eight signed weights into eight one-byte masks, one for each bitplane. A mask indexes the sum of the relevant activations. The engine reconstructs the weighted dot product by doubling through the planes and treating the sign plane as negative. The sums preserve all eight original weight bits. Q, K and V share the lookup table because they use the same normalized input.

The page-aligned group-eight workspace occupies 9 KiB across `$8000–$9FFF` and `$C000–$C3FF`. During those projections REU DMA reads model tiles into a separate window at `$C400–$CAFF`. The driver bounds that window and the model span. Resuming ordinary DMA invalidates the overlapping temporary lookup tables. In v0.7, the group-eight kernel uses unrolled, directly indexed lookups. This reduces CPU cycles while preserving the exact integer outputs.

## Causal attention and the REU cache

Every layer, position, key and value has a 96-channel int8 vector and a stored peak for reconstructing its scale. A position’s key and value use a 200-byte combined record. Four REU cache regions start at `$080000`. They use a `$8000` stride per layer for up to 128 positions and a `$10000` stride for extended contexts. Both models share the allocated cache. The current key and value are appended before attention, which reads only the live prefix through the current position. A new question or model switch resets validity and positional state.

The key pass processes all four heads in tiles of up to 40 records. It accumulates scaled attention scores and records each head’s maximum. In the value pass the engine subtracts from that maximum, looks up the negative exponential with interpolation and normalizes the weighted value sum. It reuses the final tile from the key pass before rereading the earlier prefix. The 24-bit REU driver splits requests at 512 KiB bank boundaries because the hardware counter wraps there.

[Developer build and model conversion](BUILD.md)

## Verification and timings

On the same PAL C64 Ultimate at 64 MHz and 16 MB REU, v0.7 answered the two standard Tiny 2.1 prompts in 32.442 s and 30.678 s. Combined response time dropped 10.8% from v0.6. Measurements use CIA2 PHI2 ticks and exclude model loading. Output-phase rates were 0.915 and 0.874 character tokens per second for those prompts. [Full hardware and Peddle comparison](C64_DUNGEON_COMPARISON.md#measured-on-the-c64-ultimate)

A separate Ultimate recording verified C64PROGINFO switching, resident-image reuse, and C64 answers including multiline BASIC and assembly. The v0.7 package was unpacked and checked in Peddle for both model slots, CRC recovery, the updated prompt display, and multiline answers. Peddle counts CPU cycles and models REU transfers. The hardware timings above come from the Ultimate.

[Training and independent prompt results](https://github.com/ReadyOS-C64/UltimateExperiments/blob/main/Tiny21/training/README.md)
