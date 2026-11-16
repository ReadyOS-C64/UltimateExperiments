# Tiny 2.1 v0.6 technical details

## Model and resident 6510 engine

The port uses the same checkpoint as [WollyMonjac’s Pentium/486 DOS version](https://github.com/WollyMonjac/Tiny-2.1). It implements four causal transformer layers with 96 channels, four attention heads of width 24, a 256-channel ReLU feed-forward block, and a 97-token character vocabulary. The position embeddings are learned and the context contains 128 positions. The token embedding also supplies the output matrix.

ca65 and ld65 build a resident 6502/6510 inference engine. The program streams weight and cache tiles through the REU and uses the same routine for all four layers. Cold boot loads and checks the model. Inference uses resident code with no per-layer overlays.

## Fixed-point arithmetic

Residuals, normalization inputs and logits use signed Q16.16. Each dense projection packs activations into signed 16-bit integers with a shared right-shift exponent chosen from the largest magnitude. Weight rows retain their original signed int8 values. Each row’s scale becomes Q0.24 on conversion. The engine accumulates signed products before applying the row scale and shared exponent, rounding to nearest with ties away from zero.

RMS normalization sums squares in a widened accumulator before taking an integer square root and applying Q4.12 gains. The fixed-point path retains fractional guard bits in the square root. ReLU clamps negative feed-forward activations to zero. Greedy decoding selects the largest logit after row rescaling, and ties keep the first vocabulary entry.

## Lookup tables and packed weights

The compact multiplier uses the quarter-square identity to replace byte products with table lookups and subtraction. The v3 model layout keeps these compact kernels for F2 and the embedding paths. Q, K, V and F1 instead use group-eight subset-sum tables, while O uses groups of four.

For a group of eight packed activations, the 6510 computes all 256 subset sums and stores each in three bytes. Offline packing transposes eight signed weights into eight one-byte masks, one for each bitplane. A mask indexes the sum of the relevant activations. The engine reconstructs the weighted dot product by doubling through the planes and treating the sign plane as negative. The sums preserve all eight original weight bits. Q, K and V share the lookup table because they use the same normalized input.

The page-aligned group-eight workspace occupies 9 KiB across `$8000–$9FFF` and `$C000–$C3FF`. During those projections REU DMA reads model tiles into a separate window at `$C400–$CAFF`. The driver bounds that window and the model span. Resuming ordinary DMA invalidates the overlapping temporary lookup tables. The final v3 model image still occupies 380,995 bytes.

## Causal attention and the REU cache

Every layer, position, key and value has a 96-channel int8 vector and a stored peak for reconstructing its scale. A position’s key and value use a 200-byte combined record. Four REU cache regions start at `$080000`, with a `$8000` stride per layer. The current key and value are appended before attention, which reads only the live prefix through the current position. A new question resets validity and positional state, allowing the next question to reuse the same allocated cache.

The key pass processes all four heads in tiles of up to 40 records. It accumulates scaled attention scores and records each head’s maximum. In the value pass the engine subtracts from that maximum, looks up the negative exponential with interpolation and normalizes the weighted value sum. It reuses the final tile from the key pass before rereading the earlier prefix. The 24-bit REU driver splits requests at 512 KiB bank boundaries because the hardware counter wraps there.

## Verification and timings

Peddle preloads the model into the modeled REU with a direct host copy. Real linked assembly performs model admission, REU access and inference. Version 0.6 reproduced all checked logits and answers for the 64-prompt fixed-point holdout and used 10.92% fewer total CPU cycles than the previous wide group-four build. The separate integer-versus-original comparison reproduced 63 of 64 complete answers and 2,408 of 2,415 teacher-forced choices.

On a PAL Ultimate at verified 64 MHz, the reported times came from the CIA2 PHI2 clock. The full 128-position case completed in 213.084 s, rejected overflow, and then answered a new question using the same model. The device verified all 32 REU banks with the 16 MB setting. The two standard prompts reached 0.795–0.829 generated characters per second measured from first output through completion, including stopping overhead.
