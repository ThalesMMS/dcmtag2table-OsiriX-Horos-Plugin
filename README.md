# dcmtag2table Horos Plugin

Horos plugin that exports DICOM metadata (one row per series) to a CSV file using a bundled Python pipeline.

The core DICOM metadata extraction and processing logic of this plugin is powered by [kitamura-felipe](https://github.com/kitamura-felipe)'s  [dcmtag2table](https://github.com/kitamura-felipe/dcmtag2table) project. This plugin serves as a macOS/Horos integration wrapper to bring that functionality directly into the medical imaging viewer.

---

## Status

Working extraction plugin. Runs `python_script/main.py`, prints progress to the Xcode console, and shows an alert with the CSV path and row count.

---

## Overview

- Menu item: `Plugins > Database > dcmtag2table`
- Works directly from the Database window — no need to open a study
- If studies/series are selected in the browser, exports only those; otherwise exports the entire database
- Action: selects one representative DICOM per series and exports metadata to CSV
- UI: shows a completion alert with the output path and row count
- Output: timestamped CSV in `~/dcmtag2table-output`
- Optional tag override file: `~/dcmtag2table-output/tags.txt` (one tag per line, `#` for comments)

---

## Requirements

- macOS 11+ (tested on Horos 4.x)
- Xcode 15/16+ for building the plugin
- Python 3 available via `python3` in PATH
- Python dependencies installed (see `python_script/requirements.txt`)

---

## Quick Build & Install

1. **Build the plugin**
   ```bash
   xcodebuild \
     -project dcmtag2table-Horos-Plugin/dcmtag2tableHorosPlugin.xcodeproj \
     -configuration Release \
     -target dcmtag2tableHorosPlugin \
     build
   ```

2. **Install into Horos**
   ```bash
   PLUGIN_SRC="dcmtag2table-Horos-Plugin/build/Release/dcmtag2tableHorosPlugin.osirixplugin"
   PLUGIN_DST="$HOME/Library/Application Support/Horos/Plugins/"

   rm -rf "$PLUGIN_DST/dcmtag2tableHorosPlugin.osirixplugin"
   cp -R "$PLUGIN_SRC" "$PLUGIN_DST"
   codesign --force --deep --sign - "$PLUGIN_DST/dcmtag2tableHorosPlugin.osirixplugin"
   ```

3. **Launch Horos** and confirm the entry under `Plugins > Database > dcmtag2table`.

---

## Using the Plugin

1. In the Horos Database window, optionally select the studies/series you want to export.
2. Choose `Plugins > Database > dcmtag2table`.
3. Progress logs appear in the Horos console (or Xcode if debugging).
4. An alert appears with the CSV path and row count.
5. (Optional) Create `~/dcmtag2table-output/tags.txt` to override the default tag list.

---

## Repository Layout

```
dcmtag2table-Horos-Plugin/                # Horos plugin sources (Xcode project)
dcmtag2table-Horos-Plugin/python_script/  # Bundled Python entrypoint + vendored dcmtag2table module
dcmtag2table/                             # Original dcmtag2table Python library
```

---

## License

Apache 2.0. See `LICENSE`.
