# Release packaging guide

This project is not ready for a stable `1.0.0` release yet.
Until the checks below are routinely satisfied, publish only prereleases using `0.y.z` tags such as `v0.1.0` or `v0.1.0-rc.1`.

## Versioning strategy

- Use `v0.y.z` tags while APIs, packaging, and install behavior may still change.
- Use `-rc.N` suffixes when you want a testable release candidate before a wider prerelease.
- Reserve `v1.0.0` for the first release that meets the stable-release gates below.

## Prerelease checklist

Before creating a prerelease:

1. Confirm the plugin builds successfully for the intended target (`horos`, `osirix`, or `both`) using `./dcmtag2table-Horos-Plugin/build.sh ...`.
2. Verify the expected zip artifacts exist under `Releases/Horos/` and/or `Releases/OsiriX/`.
3. Smoke-test installation on the target app and confirm the menu entry appears under `Plugins > Database > dcmtag2table`.
4. Run the plugin on a safe local sample dataset and confirm a CSV is produced in `~/dcmtag2table-output/`.
5. Update `CHANGELOG.md` with user-facing changes.
6. Create or update GitHub release notes, including which platform artifacts are attached and how they were validated.

## Stable-release gates

Do not cut `v1.0.0` until all of the following are true:

- Both Horos and OsiriX packaging paths are reproducible by following the documented build steps.
- At least one install-and-run smoke test has been documented for each supported platform.
- The repository has an explicit changelog discipline and a repeatable prerelease process.
- Release artifacts are published through GitHub Releases instead of relying on ad hoc checked-in files alone.
- Known limitations and supported environment assumptions are documented clearly enough for outside users.

## Suggested first real release

When the checklist is passing consistently, start with a prerelease such as `v0.1.0` and attach the built `.osirixplugin.zip` files for the supported platform(s). Promote to `v1.0.0` only after the stable-release gates are met.
