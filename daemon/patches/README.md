# Patch exports and candidates

Nothing here is used to set up or build `ecashd` or Lotus V2. Those stacks are commits in
`daemon/ecashd` and `daemon/lotusd`; see `daemon/AGENTS.md`.

- `ecash/`, `v2/`: frozen exports from 2026-10-22. They no longer match the stacks, so don't
  edit them or read them as current. Release and metadata tests still read them, so they
  stay until those consumers are moved.
- `v1/`, `doged/`, `doged-reference/`, `bchn/`, `bitcoin/`: exports and optional candidates
  that release and feature-planning tooling still reads.
