/*
 * A synthetic AVX2 unsigned 5-bit weight x signed int8 activation dot-product.
 * NOT a GGUF Q5_K kernel: GGUF block layouts, quant scales and min corrections
 * are intentionally absent. Supports exploring Zen 1 execution, not production.
 */
#include <immintrin.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int64_t dot_scalar(const uint8_t *w, const int8_t *x, size_t n) {
    int64_t sum = 0;
    for (size_t i = 0; i < n; i++) sum += (int64_t)w[i] * x[i];
    return sum;
}

/* Signed-saturated pairwise sums are safe for unsigned w in 0..31 and
 * signed activations in -128..127: each pair is in [-7936,+7874]. */
static int64_t dot_avx2(const uint8_t *w, const int8_t *x, size_t n) {
    const __m256i ones = _mm256_set1_epi16(1);
    int64_t result = 0;
    size_t i = 0;
    while (i + 32 <= n) {
        __m256i accumulator = _mm256_setzero_si256();
        size_t chunks = 0;
        while (i + 32 <= n && chunks < 1024) {
            const __m256i weights = _mm256_loadu_si256((const __m256i *)(const void *)(w + i));
            const __m256i activations = _mm256_loadu_si256((const __m256i *)(const void *)(x + i));
            const __m256i pair16 = _mm256_maddubs_epi16(weights, activations);
            const __m256i four32 = _mm256_madd_epi16(pair16, ones);
            accumulator = _mm256_add_epi32(accumulator, four32);
            i += 32;
            chunks++;
        }
        int32_t lanes[8];
        _mm256_storeu_si256((__m256i *)(void *)lanes, accumulator);
        for (unsigned k = 0; k < 8; k++) result += lanes[k];
    }
    for (; i < n; i++) result += (int64_t)w[i] * x[i];
    return result;
}

/* Synthetic packed Q5, NOT GGUF Q5_K layout. Used solely to check unpack logic. */
static void unpack_synthetic_q5(uint8_t *out, const uint8_t *lo, const uint8_t *hi, size_t n) {
    for (size_t i = 0; i < n; i++) {
        const uint8_t low_nibble = (i % 2) ? (lo[i / 2] >> 4) : (lo[i / 2] & 15);
        const uint8_t high_bit = (hi[i / 8] >> (i % 8)) & 1;
        out[i] = low_nibble | (high_bit << 4);
    }
}

static uint32_t rng_state = UINT32_C(0x12345678);
static uint32_t rng_next(void) {
    uint32_t x = rng_state;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    return (rng_state = x);
}

static int exercise(size_t n, unsigned flavor) {
    uint8_t *w = malloc(n ? n : 1);
    int8_t *x = malloc(n ? n : 1);
    uint8_t *lo = calloc((n + 1) / 2 + 1, 1);
    uint8_t *hi = calloc((n + 7) / 8 + 1, 1);
    uint8_t *unpacked = malloc(n ? n : 1);
    if (!w || !x || !lo || !hi || !unpacked) {
        fprintf(stderr, "allocation failed\n");
        free(w); free(x); free(lo); free(hi); free(unpacked);
        return 1;
    }
    for (size_t i = 0; i < n; i++) {
        if (flavor == 0) { w[i] = 31; x[i] = -128; }
        else if (flavor == 1) { w[i] = 31; x[i] = 127; }
        else if (flavor == 2) { w[i] = (i & 1) ? 31 : 0; x[i] = (i & 1) ? -128 : 127; }
        else { w[i] = (uint8_t)(rng_next() % 32); x[i] = (int8_t)(rng_next() & 255); }
        lo[i / 2] |= (uint8_t)((w[i] & 15) << ((i & 1) * 4));
        hi[i / 8] |= (uint8_t)(((w[i] >> 4) & 1) << (i & 7));
    }
    unpack_synthetic_q5(unpacked, lo, hi, n);
    int fail = memcmp(w, unpacked, n) != 0;
    const int64_t reference = dot_scalar(w, x, n);
    const int64_t simd = dot_avx2(w, x, n);
    if (fail || reference != simd) {
        fprintf(stderr, "FAIL n=%zu flavor=%u expected=%" PRId64 " got=%" PRId64 " unpack=%d\n",
                n, flavor, reference, simd, fail);
        fail = 1;
    }
    free(w); free(x); free(lo); free(hi); free(unpacked);
    return fail;
}

int main(void) {
    const size_t lengths[] = {0,1,2,3,7,31,32,33,63,64,65,127,255,256,257,1023,4096,8192,65536,1000000};
    for (size_t k = 0; k < sizeof(lengths)/sizeof(lengths[0]); k++) {
        for (unsigned flavor = 0; flavor < 10; flavor++) {
            if (exercise(lengths[k], flavor)) return 1;
        }
    }
    puts("PASS: 200 synthetic u5×s8 cases, scalar vs AVX2 plus synthetic bit-unpack");
    return 0;
}
