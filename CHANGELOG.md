# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-09-30

This release contains no changes to camera behaviour. It fixes the Android build
and release pipeline, which could not produce an installable APK, and introduces
versioned, reproducible releases.

### Added

- `scripts/build-web.mjs` — stages the PWA into `www/` so Capacitor receives a
  valid `webDir`. The script also fails the build when `service-worker.js` caches
  a file that is not present in the staged output, which previously would have
  shipped a silently broken offline cache.
- `.gitignore` for `node_modules/`, the generated `android/`/`ios/` native
  projects, the staged `www/` output and build artifacts.
- `CHANGELOG.md`, and a `Releases` section in the README describing how to cut
  a release.
- Release workflow now installs the exact Android SDK platform and build-tools
  that the generated Capacitor project requires, instead of assuming the runner
  image already has them.
- Release workflow now derives `versionCode`/`versionName` from the release
  version and emits a versioned APK filename
  (`pixel-ai-camera-<version>-debug.apk`).
- Release workflow now runs on pull requests that touch release plumbing, so the
  build is validated before a tag is pushed.
- `package-lock.json` is committed and CI installs with `npm ci` for
  reproducible builds. Gradle caches are restored between runs.

### Changed

- `webDir` changed from `.` to `www`. Capacitor rejects `.`, `./`, `..`, `../`
  and `""` as `webDir`, so `npx cap sync android` always failed with
  `"." is not a valid value for webDir` and no APK was ever produced.
- Capacitor dependencies pinned to `8.5.2` instead of `latest`, so a release is
  no longer silently rebuilt against whatever is newest on publish day.
- CI toolchain updated to Node 22 and JDK 21 (was Node 20 and JDK 17). Capacitor
  8 requires Node >= 22, and its Android Gradle Plugin 8.13 / Gradle 8.14.3
  combination requires JDK 21.
- `cap:add` and `cap:sync` scripts now stage `www/` first.
- Service worker cache bumped to `pixel-ai-camera-v2.0.0`.
- `app.js` reports version `2.0.0` instead of the `rework-2026-09` codename.

### Fixed

- Android APK builds and tagged GitHub releases now succeed. Previously the
  `copy android` step of `npx cap add android` failed, which also broke the
  subsequent `cap update android` step.
- `npx cap add android` is now idempotent, so re-running the workflow does not
  fail on an existing `android/` project.

## [1.0.0] - 2026-09

Initial modular release: capability-driven camera core, zoom and lens routing,
capture and processing pipeline, vision and tracking services, local gallery,
diagnostics and the PWA offline shell.
