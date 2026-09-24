#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static int parse_int(const char *value) {
    char *end = NULL;
    long parsed = strtol(value, &end, 10);
    if (end == value || *end != '\0' || parsed < 0 || parsed > 1000000) {
        return -1;
    }
    return (int)parsed;
}

static int write_all(int descriptor, const char *value, size_t length) {
    size_t offset = 0;
    while (offset < length) {
        ssize_t count = write(descriptor, value + offset, length - offset);
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count <= 0) {
            return 1;
        }
        offset += (size_t)count;
    }
    return 0;
}

static int sleep_ms(int milliseconds) {
    struct timespec duration;
    duration.tv_sec = milliseconds / 1000;
    duration.tv_nsec = (long)(milliseconds % 1000) * 1000000L;
    while (nanosleep(&duration, &duration) != 0 && errno == EINTR) {
    }
    return 0;
}

static int valid_marker_name(const char *name) {
    if (*name == '\0' || strcmp(name, ".") == 0 || strcmp(name, "..") == 0) {
        return 0;
    }
    for (const char *cursor = name; *cursor != '\0'; cursor++) {
        if (*cursor == '/') {
            return 0;
        }
    }
    return 1;
}

static int write_marker(const char *name) {
    if (!valid_marker_name(name)) {
        return 1;
    }
    int descriptor = open(name, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (descriptor < 0) {
        return 1;
    }
    int result = write_all(descriptor, "created", 7);
    close(descriptor);
    return result;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        return 64;
    }
    if (strcmp(argv[1], "argv") == 0) {
        for (int index = 2; index < argc; index++) {
            if (write_all(STDOUT_FILENO, argv[index], strlen(argv[index])) != 0 ||
                write_all(STDOUT_FILENO, "\0", 1) != 0) {
                return 74;
            }
        }
        return 0;
    }
    if (strcmp(argv[1], "env") == 0) {
        const char *names[] = {"LANG", "LC_ALL", "PATH", "SAFETYBOX_DEV_PARENT_SECRET"};
        for (size_t index = 0; index < sizeof(names) / sizeof(names[0]); index++) {
            const char *value = getenv(names[index]);
            dprintf(STDOUT_FILENO, "%s=%s%c", names[index], value == NULL ? "<absent>" : value, 0);
        }
        return 0;
    }
    if (strcmp(argv[1], "cwd") == 0 && argc == 2) {
        char cwd[4096];
        if (getcwd(cwd, sizeof(cwd)) == NULL) {
            return 73;
        }
        return write_all(STDOUT_FILENO, cwd, strlen(cwd));
    }
    if (strcmp(argv[1], "nonutf8") == 0 && argc == 2) {
        const char stdout_bytes[] = {(char)0xff, (char)0x00, (char)0x80};
        const char stderr_bytes[] = {(char)0xfe, (char)0x00, (char)0x81};
        if (write_all(STDOUT_FILENO, stdout_bytes, sizeof(stdout_bytes)) != 0 ||
            write_all(STDERR_FILENO, stderr_bytes, sizeof(stderr_bytes)) != 0) {
            return 74;
        }
        return 0;
    }
    if (strcmp(argv[1], "marker") == 0 && argc == 3) {
        return write_marker(argv[2]);
    }
    if (strcmp(argv[1], "marker-fail") == 0 && argc == 4) {
        if (write_marker(argv[2]) != 0) {
            return 73;
        }
        return parse_int(argv[3]);
    }
    if (strcmp(argv[1], "exit") == 0 && argc == 3) {
        return parse_int(argv[2]);
    }
    if (strcmp(argv[1], "sleep") == 0 && argc == 3) {
        return sleep_ms(parse_int(argv[2]));
    }
    if (strcmp(argv[1], "ignore-term-sleep") == 0 && argc == 3) {
        signal(SIGTERM, SIG_IGN);
        return sleep_ms(parse_int(argv[2]));
    }
    if (strcmp(argv[1], "signal") == 0 && argc == 3) {
        int number = parse_int(argv[2]);
        raise(number);
        return 70;
    }
    if (strcmp(argv[1], "streams") == 0 && argc == 4) {
        int stdout_count = parse_int(argv[2]);
        int stderr_count = parse_int(argv[3]);
        for (int index = 0; index < stdout_count; index++) {
            if (write_all(STDOUT_FILENO, "S", 1) != 0) {
                return 74;
            }
        }
        for (int index = 0; index < stderr_count; index++) {
            if (write_all(STDERR_FILENO, "E", 1) != 0) {
                return 74;
            }
        }
        return 0;
    }
    return 64;
}
