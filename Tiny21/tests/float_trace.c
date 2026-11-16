/* Optional fidelity fixture adapter. Compile against the private pinned upstream source. */
#define main tiny_upstream_main
#include "TINY.C"
#undef main

static unsigned greedy_token(void)
{
    unsigned best = 0, token;
    for (token = 1; token < VOCAB; ++token)
        if (score[token] > score[best])
            best = token;
    return best;
}

int main(void)
{
    char line[256], prompt[MAXQ + 1], answer[CTX + 1];
    long duration;
    int position, length;

    load_model("TINY.BIN");
    alloc_memory();
    creativity = 0;
    while (fgets(line, sizeof(line), stdin)) {
        length = clean(line, prompt);
        think(prompt, answer, &duration, NULL, NULL);
        puts(answer);
        for (position = 0; position < length; ++position) {
            step(prompt[position] - 30, position, score);
            printf("%u ", greedy_token());
        }
        step(1, position++, score);
        printf("%u", greedy_token());
        for (length = 0; answer[length] && position < CTX; ++length) {
            step(answer[length] - 30, position++, score);
            printf(" %u", greedy_token());
        }
        putchar('\n');
    }
    return 0;
}
