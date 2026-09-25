#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

/*
 * EXP-016 development-only native process helper.
 *
 * This program is experiment infrastructure, not production code and not a
 * held-out scenario. It never invokes a shell, execs another program, opens a
 * network socket, changes privilege, or creates a descendant. Writes are
 * limited to a validated basename beneath the supplied cwd. Output and sleep
 * sizes are bounded by constants below.
 */

#define MAX_STREAM_BYTES 131072U
#define MAX_SLEEP_MS 1800U
#define ABSENT_LENGTH UINT32_MAX

static int write_all(int fd, const void *buffer, size_t length) {
    const unsigned char *cursor = buffer;
    while (length > 0U) {
        ssize_t count = write(fd, cursor, length);
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count <= 0) {
            return 0;
        }
        cursor += (size_t)count;
        length -= (size_t)count;
    }
    return 1;
}

static int write_u32_be(int fd, uint32_t value) {
    unsigned char encoded[4] = {
        (unsigned char)(value >> 24U),
        (unsigned char)(value >> 16U),
        (unsigned char)(value >> 8U),
        (unsigned char)value,
    };
    return write_all(fd, encoded, sizeof(encoded));
}

static int write_frame(int fd, const void *value, size_t length) {
    if (length > UINT32_MAX) {
        return 0;
    }
    return write_u32_be(fd, (uint32_t)length) && write_all(fd, value, length);
}

static int parse_uint(const char *text, unsigned int maximum, unsigned int *out) {
    char *end = NULL;
    errno = 0;
    unsigned long value = strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value > maximum) {
        return 0;
    }
    *out = (unsigned int)value;
    return 1;
}

static int emit_argv(int argc, char **argv) {
    static const unsigned char magic[] = {'E', '1', '6', 'A'};
    uint32_t count = argc > 2 ? (uint32_t)(argc - 2) : 0U;
    if (!write_all(STDOUT_FILENO, magic, sizeof(magic)) ||
        !write_u32_be(STDOUT_FILENO, count)) {
        return 74;
    }
    for (int index = 2; index < argc; index++) {
        size_t length = strlen(argv[index]);
        if (!write_frame(STDOUT_FILENO, argv[index], length)) {
            return 74;
        }
    }
    return 0;
}

static int emit_environment(void) {
    static const unsigned char magic[] = {'E', '1', '6', 'E'};
    static const char *const keys[] = {
        "LANG", "LC_ALL", "PATH", "HOME", "EXP016_PARENT_SECRET"
    };
    uint32_t count = (uint32_t)(sizeof(keys) / sizeof(keys[0]));
    if (!write_all(STDOUT_FILENO, magic, sizeof(magic)) ||
        !write_u32_be(STDOUT_FILENO, count)) {
        return 74;
    }
    for (uint32_t index = 0; index < count; index++) {
        const char *value = getenv(keys[index]);
        if (!write_frame(STDOUT_FILENO, keys[index], strlen(keys[index]))) {
            return 74;
        }
        if (value == NULL) {
            if (!write_u32_be(STDOUT_FILENO, ABSENT_LENGTH)) {
                return 74;
            }
        } else if (!write_frame(STDOUT_FILENO, value, strlen(value))) {
            return 74;
        }
    }
    return 0;
}

static int emit_cwd(void) {
    static const unsigned char magic[] = {'E', '1', '6', 'C'};
    char buffer[4096];
    if (getcwd(buffer, sizeof(buffer)) == NULL) {
        return 72;
    }
    return write_all(STDOUT_FILENO, magic, sizeof(magic)) &&
                   write_frame(STDOUT_FILENO, buffer, strlen(buffer))
               ? 0
               : 74;
}

static int emit_pattern(int fd, unsigned int count, const unsigned char *pattern,
                        size_t pattern_length) {
    unsigned char buffer[4096];
    for (size_t index = 0; index < sizeof(buffer); index++) {
        buffer[index] = pattern[index % pattern_length];
    }
    unsigned int remaining = count;
    while (remaining > 0U) {
        size_t chunk = remaining < sizeof(buffer) ? remaining : sizeof(buffer);
        if (!write_all(fd, buffer, chunk)) {
            return 0;
        }
        remaining -= (unsigned int)chunk;
    }
    return 1;
}

static int sleep_ms(unsigned int milliseconds) {
    struct timespec remaining = {
        .tv_sec = (time_t)(milliseconds / 1000U),
        .tv_nsec = (long)(milliseconds % 1000U) * 1000000L,
    };
    while (nanosleep(&remaining, &remaining) != 0) {
        if (errno != EINTR) {
            return 71;
        }
    }
    return 0;
}

static int valid_marker_name(const char *name) {
    size_t length = strlen(name);
    if (length == 0U || length > 96U || strcmp(name, ".") == 0 ||
        strcmp(name, "..") == 0) {
        return 0;
    }
    for (const char *cursor = name; *cursor != '\0'; cursor++) {
        unsigned char value = (unsigned char)*cursor;
        if (!(value == '-' || value == '_' || value == '.' ||
              (value >= '0' && value <= '9') ||
              (value >= 'A' && value <= 'Z') ||
              (value >= 'a' && value <= 'z'))) {
            return 0;
        }
    }
    return 1;
}

static int write_marker(const char *name) {
    static const unsigned char payload[] = {'E', 'X', 'P', '0', '1', '6', 0x00, 0xa6};
    if (!valid_marker_name(name)) {
        return 65;
    }
    int fd = open(name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return 73;
    }
    int ok = write_all(fd, payload, sizeof(payload));
    if (close(fd) != 0) {
        ok = 0;
    }
    return ok ? 0 : 74;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        return 64;
    }
    if (strcmp(argv[1], "argv") == 0) {
        return emit_argv(argc, argv);
    }
    if (strcmp(argv[1], "env") == 0 && argc == 2) {
        return emit_environment();
    }
    if (strcmp(argv[1], "cwd") == 0 && argc == 2) {
        return emit_cwd();
    }
    if ((strcmp(argv[1], "stdout") == 0 || strcmp(argv[1], "stderr") == 0) && argc == 3) {
        unsigned int count = 0U;
        if (!parse_uint(argv[2], MAX_STREAM_BYTES, &count)) {
            return 65;
        }
        static const unsigned char out_pattern[] = {'O', '1', '6', ':'};
        static const unsigned char err_pattern[] = {'E', '1', '6', ':'};
        int fd = strcmp(argv[1], "stdout") == 0 ? STDOUT_FILENO : STDERR_FILENO;
        const unsigned char *pattern = fd == STDOUT_FILENO ? out_pattern : err_pattern;
        return emit_pattern(fd, count, pattern, 4U) ? 0 : 74;
    }
    if (strcmp(argv[1], "both") == 0 && argc == 4) {
        unsigned int out_count = 0U;
        unsigned int err_count = 0U;
        static const unsigned char out_pattern[] = {'O', '1', '6', ':'};
        static const unsigned char err_pattern[] = {'E', '1', '6', ':'};
        if (!parse_uint(argv[2], MAX_STREAM_BYTES, &out_count) ||
            !parse_uint(argv[3], MAX_STREAM_BYTES, &err_count)) {
            return 65;
        }
        return emit_pattern(STDOUT_FILENO, out_count, out_pattern, 4U) &&
                       emit_pattern(STDERR_FILENO, err_count, err_pattern, 4U)
                   ? 0
                   : 74;
    }
    if (strcmp(argv[1], "exit") == 0 && argc == 3) {
        unsigned int code = 0U;
        return parse_uint(argv[2], 125U, &code) ? (int)code : 65;
    }
    if ((strcmp(argv[1], "sleep") == 0 ||
         strcmp(argv[1], "ignore-term-sleep") == 0) && argc == 3) {
        unsigned int milliseconds = 0U;
        if (!parse_uint(argv[2], MAX_SLEEP_MS, &milliseconds)) {
            return 65;
        }
        if (strcmp(argv[1], "ignore-term-sleep") == 0) {
            signal(SIGTERM, SIG_IGN);
        }
        return sleep_ms(milliseconds);
    }
    if (strcmp(argv[1], "signal") == 0 && argc == 3) {
        unsigned int number = 0U;
        if (!parse_uint(argv[2], 64U, &number) || number == 0U) {
            return 65;
        }
        return raise((int)number) == 0 ? 70 : 71;
    }
    if (strcmp(argv[1], "marker") == 0 && argc == 3) {
        return write_marker(argv[2]);
    }
    if (strcmp(argv[1], "marker-then-exit") == 0 && argc == 4) {
        unsigned int code = 0U;
        if (!parse_uint(argv[3], 125U, &code) || write_marker(argv[2]) != 0) {
            return 65;
        }
        return (int)code;
    }
    if (strcmp(argv[1], "marker-then-sleep") == 0 && argc == 4) {
        unsigned int milliseconds = 0U;
        if (!parse_uint(argv[3], MAX_SLEEP_MS, &milliseconds) ||
            write_marker(argv[2]) != 0) {
            return 65;
        }
        return sleep_ms(milliseconds);
    }
    return 64;
}
