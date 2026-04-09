# Contributing

Thank you for your interest in contributing to the dcmtag2table plugin for Horos & OsiriX!

## Where to Start

This is a small OsiriX/Horos plugin with a clear scope: exporting DICOM metadata from the Database window to CSV.

**Good first contributions:**

- Bug reports (use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.yml) template)
- Clarifying documentation or README tweaks
- Simple fixes (typos, small UI labels, build script improvements)

**Before starting larger work:**

- Open an issue to discuss the change
- Check existing issues to avoid duplicates

## Building

See the main [`README.md`](README.md) under "Building from Source."

Required:

- macOS 11+
- Xcode 15/16+
- Python 3 in PATH

Use the provided `build.sh` script:

```bash
cd dcmtag2table-Horos-Plugin
./build.sh both  # or: horos | osirix
```

## Code of Conduct

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md) in this repository.

## Reporting Issues

- **Bug reports:** Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.yml)
- **Feature requests:** Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.yml)
- **Security:** See [SECURITY.md](SECURITY.md)
- **Support:** See [SUPPORT.md](SUPPORT.md)

## Pull Requests

- Keep changes small and focused
- Follow the existing code style
- No PHI (Protected Health Information) in code or comments
- Add tests only if they are trivial and proportionate
- Describe how you tested changes in the PR description

We appreciate your help!
