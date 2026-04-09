# Support & FAQ

## Installation Help

### "Plugin not appearing in the menu"

- Ensure the `.osirixplugin` file is placed in the correct folder:
  - **Horos:** `~/Library/Application Support/Horos/Plugins/`
  - **OsiriX:** `~/Library/Application Support/OsiriX/Plugins/`
- Restart Horos/OsiriX completely
- Confirm via `Plugins > Database` that `dcmtag2table` appears

### "Build fails with Xcode"

- Ensure you're using Xcode 15 or 16
- Check that `python3` is in your PATH
- Try the build script:
  ```bash
  cd dcmtag2table-Horos-Plugin
  ./build.sh both
  ```
- Clean previous artifacts if needed:
  ```bash
  xcodebuild clean -project dcmtag2tableHorosPlugin.xcodeproj
  ```

## Usage Questions

### "Where does the CSV go?"

By default, output is written to `~/dcmtag2table-output/` with timestamped filenames.

### "How do I change the exported tags?"

Create `~/dcmtag2table-output/tags.txt` with one DICOM keyword per line.
The plugin will respect this list instead of using the default tag set.

### "How do I build the inverted index?"

See the README section "Inverted Index Script (Post-processing)" for details.

## Troubleshooting

### Console logs

Open Horos/OsiriX Console (inside the app) to view plugin logs after running `dcmtag2table`.

### PHI and Privacy

This plugin exports DICOM metadata only. It does **not** export image pixels or PHI by default.
If you use the inverted-index script on real patient data, ensure you comply with local regulations
and institutional policies. Do **not** share CSV exports or indexes on public repositories.

## Getting Help

- **Support & FAQs:** This file
- **Bug Reports:** Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.yml)
- **Feature Requests:** Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.yml)
- **Security:** See [SECURITY.md](SECURITY.md)

## License

This plugin is released under Apache 2.0. See `LICENSE`.
