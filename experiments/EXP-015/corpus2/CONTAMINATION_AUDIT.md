# Contamination audit

Corpus@2 uses `C2-*` identifiers, `/workbench/ledger` logical resources, and
the schema-v2 generated helper recipe, not the retired Corpus@1 heldout probe or
DEV-PROC helper/control tuple. The integrity gate keeps Corpus@1 data separate;
no scenario JSON object or pair record is copied verbatim. Schema-v2 proof IDs
are `DEV-SCHEMA-*` and are absent. Structural overlap is limited to required
PMED concepts (exec/cwd capabilities, native argv tuples, and fixture kinds).
