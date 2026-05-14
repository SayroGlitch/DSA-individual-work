#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

// ─── Phrase list ──────────────────────────────────────────────

#define MAX_PHRASES 4096

typedef struct {
    char phrase[256];
    int  score;
    char category[64];
} Phrase;

static Phrase phrases[MAX_PHRASES];
static int    phrase_count = 0;
static int    loaded       = 0;

static void clear_phrases() {
    phrase_count = 0;
    memset(phrases, 0, sizeof(phrases));
}

// ─── JSON parser ─────────────────────────────────────────────
// Format: "phrase": {"score": N, "category": "..."}

static void parse_words_json(const char *json) {
    const char *p = json;

    while (*p) {
        // find opening quote of a key
        while (*p && *p != '"') p++;
        if (!*p) break;
        p++; // skip "

        // read key (phrase)
        char key[256];
        int  ki = 0;
        while (*p && *p != '"' && ki < 255)
            key[ki++] = *p++;
        key[ki] = '\0';
        if (*p == '"') p++;

        // skip : and {
        while (*p && *p != '{') p++;
        if (!*p) break;
        p++;

        // read score
        const char *sc = strstr(p, "\"score\"");
        const char *ca = strstr(p, "\"category\"");
        const char *cl = strchr(p, '}');

        if (!sc || !cl || sc > cl) { p = cl ? cl + 1 : p + 1; continue; }

        // parse score value
        const char *sv = sc + 7;
        while (*sv && (*sv < '0' || *sv > '9')) sv++;
        int score = atoi(sv);

        // parse category value
        char category[64] = "";
        if (ca && ca < cl) {
            const char *cv = ca + 10;
            while (*cv && *cv != '"') cv++;
            if (*cv == '"') cv++;
            int ci = 0;
            while (*cv && *cv != '"' && ci < 63)
                category[ci++] = *cv++;
            category[ci] = '\0';
        }

        if (phrase_count < MAX_PHRASES && ki > 0) {
            // lowercase the phrase
            for (int i = 0; key[i]; i++)
                key[i] = tolower((unsigned char)key[i]);
            strncpy(phrases[phrase_count].phrase,   key,      255);
            strncpy(phrases[phrase_count].category, category,  63);
            phrases[phrase_count].score = score;
            phrase_count++;
        }

        p = cl + 1;
    }
}

static void load_words_json() {
    clear_phrases();

    const char *paths[] = {
        "words.json",
        "/app/words.json",
        "../words.json"
    };

    FILE *f = NULL;
    for (int i = 0; i < 3; i++) {
        f = fopen(paths[i], "r");
        if (f) break;
    }

    if (!f) {
        fprintf(stderr, "[scorer] WARNING: words.json not found\n");
        return;
    }

    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    rewind(f);

    char *buf = (char *)malloc(len + 1);
    if (!buf) { fclose(f); return; }
    fread(buf, 1, len, f);
    buf[len] = '\0';
    fclose(f);

    // lowercase entire buffer for matching
    for (long i = 0; i < len; i++)
        buf[i] = tolower((unsigned char)buf[i]);

    parse_words_json(buf);
    free(buf);
}

// ─── Scorer ───────────────────────────────────────────────────

void reload_words() {
    load_words_json();
    loaded = 1;
}

int score_text(const char *text) {
    if (!loaded) {
        load_words_json();
        loaded = 1;
    }
    if (!text || !*text) return 0;

    // lowercase copy of input
    char buf[4096];
    strncpy(buf, text, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';
    for (int i = 0; buf[i]; i++)
        buf[i] = tolower((unsigned char)buf[i]);

    int total = 0;

    // sort phrases by length descending so longer phrases match first
    // (simple insertion sort since phrase_count is small)
    for (int i = 1; i < phrase_count; i++) {
        Phrase tmp = phrases[i];
        int j = i - 1;
        while (j >= 0 && strlen(phrases[j].phrase) < strlen(tmp.phrase)) {
            phrases[j + 1] = phrases[j];
            j--;
        }
        phrases[j + 1] = tmp;
    }

    for (int i = 0; i < phrase_count; i++) {
        const char *ph  = phrases[i].phrase;
        size_t      plen = strlen(ph);
        const char *pos = buf;

        while ((pos = strstr(pos, ph)) != NULL) {
            // check word boundaries
            int start = (int)(pos - buf);
            int end   = start + (int)plen;

            int left_ok  = (start == 0 || !isalnum((unsigned char)buf[start - 1]));
            int right_ok = (buf[end] == '\0' || !isalnum((unsigned char)buf[end]));

            if (left_ok && right_ok) {
                total += phrases[i].score;
            }
            pos++;
        }
    }

    return total;
}
