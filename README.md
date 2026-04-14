# dcmtag2table Plugin for Horos & OsiriX

Plugin for **Horos** and **OsiriX** that exports DICOM metadata (one row per series) to a CSV file using a bundled Python pipeline.

The core DICOM metadata extraction and processing logic of this plugin is powered by [kitamura-felipe](https://github.com/kitamura-felipe)'s [dcmtag2table](https://github.com/kitamura-felipe/dcmtag2table) project. This plugin serves as a macOS integration wrapper to bring that functionality directly into the medical imaging viewer.

---

## Release Status

This repository is currently **prerelease-only**.
There are no published GitHub Releases yet, and the `Releases/` directory may be empty between packaging runs.

For now:
- build from source using the steps below, or
- use packaged `.zip` artifacts only when they are present in a prerelease or checked into `Releases/`

See [RELEASE.md](RELEASE.md) for the packaging checklist, versioning plan, and the gating criteria for the first stable release.

---

## Installation

1. Obtain the appropriate `.zip` for your platform from a prerelease or from `Releases/<Platform>/` when present
2. Unzip to get `dcmtag2tableHorosPlugin.osirixplugin`
3. Copy to the plugins folder:
   - **Horos:** `~/Library/Application Support/Horos/Plugins/`
   - **OsiriX:** `~/Library/Application Support/OsiriX/Plugins/`
4. Restart the application
5. Confirm the entry under `Plugins > Database > dcmtag2table`

---

## Using the Plugin

1. In the Database window, optionally select the studies/series you want to export
2. Choose `Plugins > Database > dcmtag2table`
3. Progress logs appear in the console
4. An alert appears with the CSV path and row count
5. (Optional) Create `~/dcmtag2table-output/tags.txt` to override the default tag list

**Output:** Timestamped CSV files in `~/dcmtag2table-output/`

---

## Building from Source

### Requirements

- macOS 11+
- Xcode 15/16+
- Python 3 available via `python3` in PATH
- Python dependencies installed (see `python_script/requirements.txt`)

### Build Script

Use the included build script to compile for either or both platforms:

```bash
cd dcmtag2table-Horos-Plugin

# Build for Horos only
./build.sh horos

# Build for OsiriX only
./build.sh osirix

# Build for both platforms
./build.sh both
```

The script will:
1. Configure the project for the target platform
2. Compile the plugin
3. Copy to `Releases/<Platform>/`
4. Create a zip file automatically

### Manual Build

```bash
# For Horos
cp dcmtag2tableHorosPlugin.xcodeproj/project_Horos.pbxproj \
   dcmtag2tableHorosPlugin.xcodeproj/project.pbxproj
cp dcmtag2tableHorosPlugin-Bridging-Header_Horos.h \
   dcmtag2tableHorosPlugin-Bridging-Header.h

# For OsiriX
cp dcmtag2tableHorosPlugin.xcodeproj/project_OsiriX.pbxproj \
   dcmtag2tableHorosPlugin.xcodeproj/project.pbxproj
cp dcmtag2tableHorosPlugin-Bridging-Header_OsiriX.h \
   dcmtag2tableHorosPlugin-Bridging-Header.h

# Then build
xcodebuild -project dcmtag2tableHorosPlugin.xcodeproj \
           -configuration Release build
```

---

## Repository Layout

```
dcmtag2table-Horos-Plugin/
├── build.sh                                    # Build script for both platforms
├── Plugin.swift                                # Main plugin source code
├── python_script/                              # Bundled Python pipeline
├── dcmtag2tableHorosPlugin.xcodeproj/
│   ├── project_Horos.pbxproj                   # Xcode project for Horos
│   └── project_OsiriX.pbxproj                  # Xcode project for OsiriX
├── dcmtag2tableHorosPlugin-Bridging-Header_Horos.h
├── dcmtag2tableHorosPlugin-Bridging-Header_OsiriX.h
├── Horos.framework/                            # Horos SDK
└── OsiriXAPI.framework/                        # OsiriX SDK
dcmtag2table/                                   # Original dcmtag2table Python library
Releases/
├── Horos/                                      # Pre-built plugin for Horos
└── OsiriX/                                     # Pre-built plugin for OsiriX
```

---

## License

Apache 2.0. See `LICENSE`.

---

## Versioning & Changelog

Until the project has repeatable packaging and install validation for both Horos and OsiriX, use `0.y.z` pre-1.0 versions such as `v0.1.0` or `v0.1.0-rc.1`.

Track user-facing changes in [CHANGELOG.md](CHANGELOG.md). GitHub auto-generated release notes are enabled via [`.github/release.yml`](.github/release.yml).

## Community & Support

- **[SUPPORT.md](SUPPORT.md)** — Installation, usage, and troubleshooting FAQs
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — How to contribute and build from source
- **[SECURITY.md](SECURITY.md)** — How to report security issues privately
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — Code of conduct for this project
- **Bug Reports**: [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.yml)
- **Feature Requests**: [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.yml)

> **PHI Note:** This plugin exports DICOM metadata only. Do not commit patient data
> or CSV exports to public repos. Ensure compliance with local regulations and
> institutional policies when using real patient data.

---

## Inverted Index Script (Post-processing)

This repo includes a helper script to build inverted indexes from a CSV exported
by the plugin. It is intended for offline analysis and is not bundled in the
plugin package.

Location: `dcmtag2table-Horos-Plugin/python_script/build_inverted_index.py`

Inputs:
- `--csv`: plugin CSV export
- `--tags-file`: text file with one DICOM tag keyword per line (must match CSV header)
- `--output-dir`: directory for JSON output

Outputs:
- One JSON per tag, mapping `<tag value> -> [StudyInstanceUIDs...]`
- `index.json` mapping each JSON filename to the list of keys (unique tag values)

Example:

```bash
python3 dcmtag2table-Horos-Plugin/python_script/build_inverted_index.py \
  --csv ~/dcmtag2table-output/dcmtag2table_YYYYMMDD_HHMMSS.csv \
  --tags-file ~/dcmtag2table-output/tags.txt \
  --output-dir ~/dcmtag2table-output/indexes
```

Notes:
- The only index key used is `StudyInstanceUID` (not `SeriesInstanceUID`).
- Missing values (empty, `Not found`, etc.) are skipped. Add more via `--missing-token`.
