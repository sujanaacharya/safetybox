# EXP-016 native ELF fixture design

**Artifact:** `EXP-016-NATIVE-HELPER@1`

**Role:** development and future corpus infrastructure, never production code

**Language:** C11

## Native identity and provenance

The helper source is
[`experiments/EXP-016/fixture/native_helper.c`](../../experiments/EXP-016/fixture/native_helper.c).
It is compiled before corpus authorship with `/usr/bin/cc` and these frozen flags:

```text
-std=c11 -O2 -Wall -Wextra -Werror -fno-ident -Wl,--build-id=none
```

`SOURCE_DATE_EPOCH=0` is supplied. The build script is
[`scripts/build_exp016_helper.py`](../../scripts/build_exp016_helper.py), and the exact
source checksum, compiler identity, binary checksum, ELF metadata, linkage, architecture,
and required loader are stored in
[`build_provenance.json`](../../experiments/EXP-016/fixture/build_provenance.json).

At freeze the binary is an ELF64 little-endian x86-64 PIE (`ET_DYN`, `EM_X86_64`),
dynamically linked through `/lib64/ld-linux-x86-64.so.2`. It contains no shebang and is
not an interpreted wrapper. The pre-corpus host gate must reject an architecture or
loader mismatch rather than attempt a held-out run.

## Protocol

The helper accepts one fixed mode followed by bounded mode-specific operands. It never
parses a command string.

| Mode | Behavior | Bound |
|---|---|---|
| `argv ...` | `E16A`, big-endian count, then big-endian length + bytes per argument | adapter argv limits |
| `env` | `E16E` framed values for five fixed keys | five keys |
| `cwd` | `E16C` plus framed physical cwd | 4,096-byte buffer |
| `stdout N` | deterministic `O16:` byte pattern | `N ≤ 131072` |
| `stderr N` | deterministic `E16:` byte pattern | `N ≤ 131072` |
| `both N M` | both deterministic patterns | each ≤ 131072 |
| `exit N` | normal exit | `N ≤ 125` |
| `sleep N` | bounded sleep | `N ≤ 1800 ms` |
| `ignore-term-sleep N` | ignore TERM, then bounded sleep | `N ≤ 1800 ms` |
| `signal N` | self-raise a registered safe POSIX signal | `1 ≤ N ≤ 64` |
| `marker NAME` | exclusive basename marker with fixed binary payload | name ≤ 96 bytes |
| `marker-then-exit NAME N` | marker, then normal exit | exit ≤ 125 |
| `marker-then-sleep NAME N` | marker, then bounded sleep | sleep ≤ 1800 ms |

The argv format is unambiguous even for empty strings, Unicode, spaces, quotes, and
shell-looking values. It does not rely on whitespace or line parsing. Environment absence
uses the reserved unsigned length `0xffffffff`.

## Safety constraints

The helper has no shell call, arbitrary `exec`, network operation, privilege operation,
fork/clone, descendant, background work, or unbounded output. Marker names admit only
ASCII letters, digits, dot, underscore, and hyphen; slash and traversal names are
rejected. Markers use `O_EXCL|O_NOFOLLOW`, mode `0600`, and a fixed eight-byte payload in
the supplied cwd.

The helper intentionally cannot establish child confinement. A successful marker proves
one selected effect happened; it says nothing about complete filesystem mediation.

## Development smoke requirement

Before corpus authorship, every mode is invoked directly with `shell=False`, outside
`ProcessAdapter`. The smoke proof checks framed argv, framed environment, physical cwd,
each stream mode, exit 23, short sleep, self-`SIGUSR1`, marker, marker-then-sleep, and
marker-then-exit. These concrete operands are contamination inventory and cannot be
reused exactly in the held-out corpus.
