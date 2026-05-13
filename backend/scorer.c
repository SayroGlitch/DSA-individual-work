#include <ctype.h>
#include <stdio.h>
#include <string.h>

#define MAX_TEXT 4096
#define MAX_MATCHES 256
#define MAX_NODES 12000
#define ALPHABET_SIZE 38

typedef struct {
    int next[ALPHABET_SIZE];
    int fail;
    int output_index;
} TrieNode;

typedef struct {
    char phrase[128];
    int score;
    char category[64];
} LexiconEntry;

typedef struct {
    char matched_phrases[MAX_MATCHES][128];
    char matched_categories[MAX_MATCHES][64];
    int matched_scores[MAX_MATCHES];
    int match_count;
    int total_score;
} ScanResult;

TrieNode trie[MAX_NODES];
int trie_size = 0;

int char_to_index(char c) {
    if (c >= 'a' && c <= 'z') return c - 'a';
    if (c >= '0' && c <= '9') return 26 + (c - '0');
    if (c == '\'') return 36;
    if (c == ' ') return 37;
    return -1;
}

void init_trie() {
    trie_size = 1;
    for (int i = 0; i < MAX_NODES; i++) {
        for (int j = 0; j < ALPHABET_SIZE; j++) {
            trie[i].next[j] = -1;
        }
        trie[i].fail = 0;
        trie[i].output_index = -1;
    }
}

void normalize_text_c(const char *input, char *output, int max_len) {
    int j = 0;
    int prev_space = 1;

    for (int i = 0; input[i] != '\0' && j < max_len - 1; i++) {
        unsigned char c = (unsigned char)input[i];

        if (isalnum(c) || c == '\'') {
            output[j++] = (char)tolower(c);
            prev_space = 0;
        } else {
            if (!prev_space) {
                output[j++] = ' ';
                prev_space = 1;
            }
        }
    }

    if (j > 0 && output[j - 1] == ' ') {
        j--;
    }

    output[j] = '\0';
}

void insert_pattern(const char *pattern, int pattern_index) {
    int node = 0;

    for (int i = 0; pattern[i] != '\0'; i++) {
        int idx = char_to_index(pattern[i]);
        if (idx == -1) continue;

        if (trie[node].next[idx] == -1) {
            trie[node].next[idx] = trie_size++;
        }
        node = trie[node].next[idx];
    }

    trie[node].output_index = pattern_index;
}

void build_failure_links() {
    int queue[MAX_NODES];
    int front = 0, rear = 0;

    for (int c = 0; c < ALPHABET_SIZE; c++) {
        int next_node = trie[0].next[c];
        if (next_node != -1) {
            trie[next_node].fail = 0;
            queue[rear++] = next_node;
        } else {
            trie[0].next[c] = 0;
        }
    }

    while (front < rear) {
        int current = queue[front++];

        for (int c = 0; c < ALPHABET_SIZE; c++) {
            int next_node = trie[current].next[c];

            if (next_node != -1) {
                trie[next_node].fail = trie[trie[current].fail].next[c];
                queue[rear++] = next_node;
            } else {
                trie[current].next[c] = trie[trie[current].fail].next[c];
            }
        }
    }
}

int is_word_boundary(char c) {
    return c == '\0' || c == ' ';
}

void scan_text_c(
    const char *message,
    LexiconEntry entries[],
    int entry_count,
    ScanResult *result
) {
    char normalized[MAX_TEXT];
    normalize_text_c(message, normalized, sizeof(normalized));

    result->match_count = 0;
    result->total_score = 0;

    init_trie();

    for (int i = 0; i < entry_count; i++) {
        insert_pattern(entries[i].phrase, i);
    }

    build_failure_links();

    int state = 0;
    int text_len = (int)strlen(normalized);

    for (int i = 0; i < text_len; i++) {
        int idx = char_to_index(normalized[i]);
        if (idx == -1) {
            state = 0;
            continue;
        }

        state = trie[state].next[idx];

        int temp = state;
        while (temp != 0) {
            int out = trie[temp].output_index;

            if (out != -1) {
                int phrase_len = (int)strlen(entries[out].phrase);
                int start = i - phrase_len + 1;

                char before = (start <= 0) ? ' ' : normalized[start - 1];
                char after = (i + 1 >= text_len) ? '\0' : normalized[i + 1];

                if (is_word_boundary(before) && is_word_boundary(after)) {
                    int already_added = 0;
                    for (int k = 0; k < result->match_count; k++) {
                        if (strcmp(result->matched_phrases[k], entries[out].phrase) == 0) {
                            already_added = 1;
                            break;
                        }
                    }

                    if (!already_added && result->match_count < MAX_MATCHES) {
                        strncpy(result->matched_phrases[result->match_count], entries[out].phrase, 127);
                        result->matched_phrases[result->match_count][127] = '\0';

                        strncpy(result->matched_categories[result->match_count], entries[out].category, 63);
                        result->matched_categories[result->match_count][63] = '\0';

                        result->matched_scores[result->match_count] = entries[out].score;
                        result->total_score += entries[out].score;
                        result->match_count++;
                    }
                }
            }

            temp = trie[temp].fail;
        }
    }
}

int classify_score_c(int score) {
    if (score >= 18) return 2;
    if (score >= 7) return 1;
    return 0;
}