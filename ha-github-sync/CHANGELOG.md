# Changelog

## [0.1.2] - unreleased

### Changed
- Automated version bump.

## [0.1.1] - unreleased

### Changed
- Automated version bump.

## [0.1.0] - 2026-07-04

### Added
- Initial release: export-only sync of selected HA config files to GitHub.
- Configurable include/exclude path lists.
- Hardcoded deny-list for secrets, runtime state, and privacy-sensitive files.
- YAML syntax validation before committing.
- Secret pattern scanning with warnings.
- Bidirectional mode (off by default) with validation and rollback on failure.
- Conflict detection: halts inbound sync when branches have diverged.
- Dry-run mode for safe testing.
- `/data/status.json` health/status summary.
- Process lock file to prevent overlapping sync runs.
- Automatic backup branch (`backup/pre-inbound`) before any inbound apply.
- Structured commit messages referencing changed files.
- `.ha-sync-manifest.json` written into the synced repository.
- Default `.gitignore` written to the repo on first run.
