# EXP-016 Protocol@2 governance artifacts

This directory contains versioned successors for future EXP-016 corpus authorship. It does
not contain a held-out corpus, labels, predictions, or results.

Protocol@1 remains immutable at its existing paths. Protocol@2 corrects experiment-model
defects discovered by pre-exposure adversarial review: definition/population conflation, a
strict-prefix lifecycle assumption, and adapter-shaped DIRECT_CONTROL metadata.

Machine contracts live in `contracts/`; synthetic development proof identities live in
`proofs/`. `SHA256SUMS` freezes only v2 governance artifacts and does not overwrite any v1
manifest.
