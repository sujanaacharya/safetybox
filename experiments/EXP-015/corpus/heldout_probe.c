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
 * EXP-015 held-out probe.  This is intentionally not interface-compatible with
 * tests/fixtures/process_helper.c.  It is bounded, performs no network or shell
 * work, and can create only one fixed-name note beneath its supplied cwd.
 */

static int bounded_uint(const char *text, unsigned int maximum, unsigned int *out) {
    char *end = NULL;
    errno = 0;
    unsigned long value = strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value > maximum) {
        return 0;
    }
    *out = (unsigned int)value;
    return 1;
}

static int write_bytes(int fd, const void *buffer, size_t length) {
    const unsigned char *cursor = buffer;
    while (length > 0) {
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

static int frame_arguments(int argc, char **argv) {
    uint32_t count = argc > 2 ? (uint32_t)(argc - 2) : 0;
    if (!write_bytes(STDOUT_FILENO, &count, sizeof(count))) {
        return 74;
    }
    for (int index = 2; index < argc; index++) {
        size_t raw_length = strlen(argv[index]);
        if (raw_length > UINT32_MAX) {
            return 65;
        }
        uint32_t length = (uint32_t)raw_length;
        if (!write_bytes(STDOUT_FILENO, &length, sizeof(length)) ||
            !write_bytes(STDOUT_FILENO, argv[index], raw_length)) {
            return 74;
        }
    }
    return 0;
}

static int inspect_environment(void) {
    const char *keys[] = {
        "LANG", "LC_ALL", "PATH", "HOME", "EXP015_PARENT_CANARY", "CI_JOB_TOKEN"
    };
    for (size_t index = 0; index < sizeof(keys) / sizeof(keys[0]); index++) {
        const char *value = getenv(keys[index]);
        if (dprintf(STDOUT_FILENO, "%s:%s\n", keys[index], value ? value : "ABSENT") < 0) {
            return 74;
        }
    }
    return 0;
}

static int fixed_note(void) {
    int fd = open("exp015-child-note.bin", O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return 73;
    }
    static const unsigned char payload[] = {0x45, 0x31, 0x35, 0x00, 0xa5};
    int ok = write_bytes(fd, payload, sizeof(payload));
    if (close(fd) != 0) {
        ok = 0;
    }
    return ok ? 0 : 74;
}

static int pause_for(unsigned int milliseconds) {
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

static int duplex(unsigned int out_count, unsigned int err_count) {
    static const unsigned char out_pattern[] = "O15:";
    static const unsigned char err_pattern[] = "E15:";
    for (unsigned int index = 0; index < out_count; index++) {
        if (!write_bytes(STDOUT_FILENO, &out_pattern[index % 4U], 1)) {
            return 74;
        }
    }
    for (unsigned int index = 0; index < err_count; index++) {
        if (!write_bytes(STDERR_FILENO, &err_pattern[index % 4U], 1)) {
            return 74;
        }
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        return 64;
    }
    if (strcmp(argv[1], "frame") == 0) {
        return frame_arguments(argc, argv);
    }
    if (strcmp(argv[1], "scope") == 0 && argc == 2) {
        return inspect_environment();
    }
    if (strcmp(argv[1], "location") == 0 && argc == 2) {
        char buffer[2048];
        if (getcwd(buffer, sizeof(buffer)) == NULL) {
            return 72;
        }
        return write_bytes(STDOUT_FILENO, buffer, strlen(buffer)) ? 0 : 74;
    }
    if (strcmp(argv[1], "octets") == 0 && argc == 2) {
        static const unsigned char out[] = {0x00, 0xf5, 0x7f, 0x80};
        static const unsigned char err[] = {0x9f, 0x00, 0xed, 0x42};
        return write_bytes(STDOUT_FILENO, out, sizeof(out)) &&
                       write_bytes(STDERR_FILENO, err, sizeof(err))
                   ? 0
                   : 74;
    }
    if (strcmp(argv[1], "note") == 0 && argc == 2) {
        return fixed_note();
    }
    if (strcmp(argv[1], "note-then") == 0 && argc == 3) {
        unsigned int code = 0;
        if (!bounded_uint(argv[2], 125U, &code) || fixed_note() != 0) {
            return 65;
        }
        return (int)code;
    }
    if (strcmp(argv[1], "finish") == 0 && argc == 3) {
        unsigned int code = 0;
        return bounded_uint(argv[2], 125U, &code) ? (int)code : 65;
    }
    if ((strcmp(argv[1], "pause") == 0 || strcmp(argv[1], "resist") == 0) && argc == 3) {
        unsigned int milliseconds = 0;
        if (!bounded_uint(argv[2], 1500U, &milliseconds)) {
            return 65;
        }
        if (strcmp(argv[1], "resist") == 0) {
            signal(SIGTERM, SIG_IGN);
        }
        return pause_for(milliseconds);
    }
    if (strcmp(argv[1], "self-stop") == 0 && argc == 3) {
        unsigned int number = 0;
        if (!bounded_uint(argv[2], 64U, &number) || number == 0U) {
            return 65;
        }
        return raise((int)number) == 0 ? 70 : 71;
    }
    if (strcmp(argv[1], "duplex") == 0 && argc == 4) {
        unsigned int out_count = 0;
        unsigned int err_count = 0;
        if (!bounded_uint(argv[2], 70000U, &out_count) ||
            !bounded_uint(argv[3], 70000U, &err_count)) {
            return 65;
        }
        return duplex(out_count, err_count);
    }
    return 64;
}
