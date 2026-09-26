# Lagarto Shorts

Automated Shorts factory built around GitHub Actions.

## Principles

- Cloud-only: no processing on the personal PC.
- Initial target: €0 and no payment card.
- Public GitHub repository with standard runners.
- Secrets only through GitHub Actions secrets/variables.
- Persistent state is designed to live outside ephemeral runners as the project grows.
- Content processing must use content that is authorized/licensed for reuse, with meaningful original transformation.
- Political content is not optimized for persuasion.

## Pipeline

1. Radar — monitor configured creators/sources.
2. Candidate scoring — identify moments worth reviewing.
3. Factory — transform authorized source material into vertical Shorts.
4. Publisher — upload and schedule to YouTube.
5. Analytics — collect performance snapshots.
6. Learning — adjust selection/editing rules from observed metrics.

## Current stage

Infrastructure foundation and automated health checks.
