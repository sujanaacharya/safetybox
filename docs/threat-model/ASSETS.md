# Assets

| Asset | Security properties of interest |
|---|---|
| User task and contract | Authenticity, integrity, correct task/session binding |
| Files and source repositories | Confidentiality, integrity, scoped availability |
| Credentials and secrets | Confidentiality, non-disclosure, non-use outside authorization |
| Network/API authority | Destination, method, data, rate, and cost constraints |
| Shell/host authority | Process and filesystem isolation; least privilege |
| Database data and authority | Connection, table/row/column, operation, and export scope |
| SafetyBox policies/configuration | Integrity, authenticity, controlled versioning |
| Capability and approval state | Non-forgeability, attenuation, expiry, replay resistance |
| Events, audit, and provenance | Completeness, ordering, integrity, confidentiality, retention |
| Experiment data and results | Provenance, immutability after finalization, reproducibility |
| Service resources | Availability, bounded compute/cost/storage |
| Human approvers | Accurate context, authenticated decisions, bounded authority |

Asset value and impact vary by deployment. An experiment must state which assets and properties its outcomes represent.
