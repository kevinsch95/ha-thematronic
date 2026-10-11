# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-10-11

### Added

- Pellet stove icon for the integrations list (`brand/icon.png`,
  `brand/icon@2x.png`), shown by Home Assistant 2026.3 and later.
- This changelog and a release check that the git tag matches the version in
  `manifest.json`.

## [0.1.0] - 2026-10-11

### Added

- First release: read-only integration for the Thematronic JBR-1 portal
  (jbr1.thematronic.cz).
- Setup through the Home Assistant UI, with re-authentication and options
  (update interval, raw portal signals).
- Sensors and binary sensors for every tile on the web dashboard; parts not
  used by the controller's hydraulic schema start disabled.
- English, German and Norwegian (Bokmål) translations.
- Diagnostics download with login details removed.

[Unreleased]: https://github.com/kevinsch95/ha-thematronic/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/kevinsch95/ha-thematronic/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/kevinsch95/ha-thematronic/releases/tag/v0.1.0
