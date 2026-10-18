#include <stdio.h>
#include <string.h>

#include "src/apps/readyfs/readyfs_path.h"
#include "src/apps/readyfs/readyfs_match.h"

static int fails;

static void expect_normalized(const char *text, unsigned char rc,
                              const char *expected) {
    char output[RF_PATH_MAX + 1u];
    unsigned char got;

    got = readyfs_path_normalize(text, output);
    if (got != rc || (got == RF_PATH_OK && strcmp(output, expected) != 0)) {
        fprintf(stderr, "FAIL normalize %s rc=%u output=%s\n",
                text, got, got == RF_PATH_OK ? output : "-");
        ++fails;
    }
}

static void expect_path(const char *text, unsigned char rc,
                        unsigned char endpoint, unsigned char unit,
                        unsigned char partition, unsigned char depth) {
    ReadyFsPath path;
    unsigned char got;

    got = readyfs_path_parse(text, &path);
    if (got != rc || (got == RF_PATH_OK &&
        (path.endpoint != endpoint || path.unit != unit ||
         path.partition != partition ||
         path.image_depth != depth))) {
        fprintf(stderr, "FAIL path %s rc=%u ep=%u unit=%u part=%u depth=%u\n",
                text, got, path.endpoint, path.unit, path.partition,
                path.image_depth);
        ++fails;
    }
}

int main(void) {
    char long_path[258];
    char ultimate_stem[96];

    expect_path("8:/FILE", RF_PATH_OK, RF_EP_IEC, 8u, 0u, 0u);
    expect_path("30:/FILE", RF_PATH_OK, RF_EP_IEC, 30u, 0u, 0u);
    expect_path("11.3:/folder/file", RF_PATH_OK, RF_EP_IEC, 11u, 3u, 0u);
    expect_path("11.254:/disk.d64!/file", RF_PATH_OK, RF_EP_IEC,
                11u, 254u, 1u);
    expect_path("u:/usb1/a.d81!/FILE", RF_PATH_OK,
                RF_EP_ULTIMATE, 0u, 0u, 1u);
    expect_path("s255:/folder", RF_PATH_OK, RF_EP_SOFTIEC, 255u, 0u, 0u);
    expect_path("t:/NAME", RF_PATH_OK, RF_EP_TAPE, 1u, 0u, 0u);
    expect_path("@work:/src", RF_PATH_OK, RF_EP_ALIAS, 0u, 0u, 0u);
    expect_path("7:/FILE", RF_PATH_BAD_DEVICE, 0u, 0u, 0u, 0u);
    expect_path("31:/FILE", RF_PATH_BAD_DEVICE, 0u, 0u, 0u, 0u);
    expect_path("11.255:/FILE", RF_PATH_BAD_DEVICE, 0u, 0u, 0u, 0u);
    expect_path("11.:/FILE", RF_PATH_BAD_ENDPOINT, 0u, 0u, 0u, 0u);
    expect_path("u:/bad!file", RF_PATH_BAD_SEGMENT, 0u, 0u, 0u, 0u);
    expect_path("u:/bad!", RF_PATH_BAD_SEGMENT, 0u, 0u, 0u, 0u);

    expect_normalized("u:/usb1/./folder/../file", RF_PATH_OK,
                      "u:/usb1/file");
    expect_normalized("u:/disk.d81!/one/../two", RF_PATH_OK,
                      "u:/disk.d81!/two");
    expect_normalized("u:/disk.d81!/..", RF_PATH_ESCAPE, "");
    expect_normalized("u:/..", RF_PATH_ESCAPE, "");
    expect_normalized("s3:/folder//child/.", RF_PATH_OK,
                      "s3:/folder/child");
    expect_normalized("11.3:/one/../two", RF_PATH_OK,
                      "11.3:/two");

    memset(long_path, 'a', sizeof(long_path));
    long_path[0] = 'u';
    long_path[1] = ':';
    long_path[257] = 0;
    expect_path(long_path, RF_PATH_TOO_LONG, 0u, 0u, 0u, 0u);

    if (!readyfs_path_has_parent_escape("u:/safe/../escape") ||
        readyfs_path_has_parent_escape("u:/safe/.../name")) {
        fprintf(stderr, "FAIL parent escape detection\n");
        ++fails;
    }
    if (strcmp(readyfs_path_error(RF_PATH_ESCAPE),
               "path escapes protected root") != 0) {
        fprintf(stderr, "FAIL alias escape diagnostic\n");
        ++fails;
    }
    if (!readyfs_match("*.prg", "hello.PRG") ||
        readyfs_match("*.prg", "folder/hello.prg") ||
        !readyfs_match("file?.seq", "FILE1.SEQ") ||
        readyfs_match("file?.seq", "file12.seq") ||
        !readyfs_match("**/*.prg", "hello.prg") ||
        !readyfs_match("**/*.prg", "one/two/hello.prg") ||
        !readyfs_match("disk.d81!/**", "disk.d81!/inside/file") ||
        readyfs_match("folder/*", "folder/deep/file")) {
        fprintf(stderr, "FAIL shell wildcard matching\n");
        ++fails;
    }
    strcpy(ultimate_stem,
           "[6e6573746564]/[696e73696465].[736571].SEQ");
    readyfs_match_normalize_ultimate(ultimate_stem, 1u);
    if (strcmp(ultimate_stem, "nested/inside") != 0 ||
        !readyfs_match("**/inside", ultimate_stem)) {
        fprintf(stderr, "FAIL UltimateDOS logical filter stem: %s\n",
                ultimate_stem);
        ++fails;
    }
    strcpy(ultimate_stem, "[736661].[736571].SEQ");
    readyfs_match_normalize_ultimate(ultimate_stem, 1u);
    if (strcmp(ultimate_stem, "sfa") != 0) {
        fprintf(stderr, "FAIL UltimateDOS matching type strip: %s\n",
                ultimate_stem);
        ++fails;
    }
    {
        ReadyFsUltimateMatchCall call;
        strcpy(ultimate_stem, "NESTED/inside.seq");
        /* Physical keyboard injection supplies ASCII uppercase while an
         * Ultimate host leaf can remain lowercase. */
        call.include = "**/INSIDE";
        call.exclude = 0;
        call.stem = ultimate_stem;
        call.file = 1u;
        if (!readyfs_match(RF_MATCH_ULTIMATE_FILTER,
                           (const char *)&call) ||
            strcmp(ultimate_stem, "NESTED/inside") != 0) {
            fprintf(stderr, "FAIL atomic UltimateDOS filter: %s\n",
                    ultimate_stem);
            ++fails;
        }
    }
    {
        static const char petscii_upper[] = { (char)0xC9, (char)0xCE,
            (char)0xD3, (char)0xC9, (char)0xC4, (char)0xC5, 0 };
        if (!readyfs_match(petscii_upper, "inside")) {
            fprintf(stderr, "FAIL PETSCII/ASCII case fold\n");
            ++fails;
        }
    }
    {
        static const unsigned char entry[] =
            "[6469736b31].[643831].SEQ";
        ReadyFsUltimateFindCall call;
        char access[64];
        call.wanted = "DISK1.D81";
        call.entry = entry;
        call.entry_length = sizeof(entry) - 1u;
        call.access = access;
        call.display = 0;
        if (!readyfs_match(RF_MATCH_ULTIMATE_FIND,
                           (const char *)&call) ||
            strcmp(access, "[6469736b31].[643831].SEQ") != 0) {
            fprintf(stderr, "FAIL UltimateDOS access identity: %s\n",
                    access);
            ++fails;
        }
    }
    {
        static const unsigned char entry[] = "work.seq";
        ReadyFsUltimateFindCall call;
        char access[64];
        call.entry = entry;
        call.entry_length = sizeof(entry) - 1u;
        call.access = access;
        call.display = 0;
        call.wanted = "WORK.SEQ";
        if (!readyfs_match(RF_MATCH_ULTIMATE_FIND, (const char *)&call) ||
            strcmp(access, "work.seq") != 0) {
            fprintf(stderr, "FAIL literal host extension lookup\n");
            ++fails;
        }
        call.wanted = "WORK";
        if (!readyfs_match(RF_MATCH_ULTIMATE_FIND, (const char *)&call) ||
            strcmp(access, "work.seq") != 0) {
            fprintf(stderr, "FAIL logical host extension lookup\n");
            ++fails;
        }
        call.wanted = "OTHER.SEQ";
        if (readyfs_match(RF_MATCH_ULTIMATE_FIND, (const char *)&call)) {
            fprintf(stderr, "FAIL unrelated host lookup matched\n");
            ++fails;
        }
    }
    if (fails != 0) {
        return 1;
    }
    puts("readyfs path tests passed");
    return 0;
}
