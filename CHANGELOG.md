# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project uses
calendar versioning (`YYYY.MM.N`) rather than semantic versioning.

Add new entries under `## [Unreleased]`, in the category they belong to. At release time, rename
`## [Unreleased]` to `## [<version>] - <YYYY-MM-DD>` and start a fresh `## [Unreleased]` above it.

## [Unreleased]

### Added

- A `hep.resource_usage` hook recording per-partition wall-clock time, CPU time and peak RSS.
- A warning when resolving a dataset's entry count would require reading many files.

### Changed

- Dataset entry counts are resolved from recorded `nevents` metadata first, falling back to reading
  files only when that metadata is missing.

### Fixed

- The schema-snapshot observer now correctly returns `None` for a skipped first-partition snapshot
  instead of an invalid value.

## [2026.08.1] - 2026-08-19

### Added

- Public `.api` surface exposed under the package's top-level `__all__`.
- Schema outputs and a supporting API for CLI consumers.
- Schema comparison.
- Shared counters supported in schema validation.
- A `root_tree_metadata` compile hook that can read dataset schema from `metadata_schema` when
  present.

### Changed

- Compile hooks now follow the generic component-spec contract, aligning hook specs with the rest
  of the registry.
- Standardised terminology across hook/spec parameters: `inputs` → `input`, `outputs` → `result`.

### Fixed

- Removed duplicated schema entries appearing in the output path.
