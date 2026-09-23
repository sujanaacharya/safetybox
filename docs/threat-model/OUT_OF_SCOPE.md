# Threat-Model Out of Scope

The following are excluded from initial SafetyBox effectiveness claims, not dismissed as unimportant:

- compromise of the host kernel, hypervisor, hardware root, or SafetyBox administrator;
- direct agent access to privileged resources that bypasses all configured adapters;
- physical-world safety not represented by mediated actions and deployment-specific interlocks;
- universal identification of harmful intent or truthfulness from model text;
- covert channels and side channels not exposed in canonical telemetry;
- safety of effects occurring internally within a remote third-party tool after an authorized call;
- cryptographic or operating-system isolation guarantees supplied by dependencies;
- preventing a duly authorized task issuer from deliberately defining a harmful contract;
- legal, policy, and ethical acceptability across all jurisdictions and domains;
- autonomous remediation of every compromised multi-agent or persistent-memory system.

An experiment may bring an item into scope by declaring assumptions, controls, and measurements. That does not silently broaden other claims.
