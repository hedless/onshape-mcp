# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `ONSHAPE_LENGTH_UNIT` (`in`, `mm`, `cm` or `m`) sets the unit for every length the tools take
  and report. Features are created with expressions in that unit. Defaults to inches.

### Changed

- Length fields in the analysis dataclasses lost their `_inches` suffix
  (`InstancePositionInfo.position_x`, `OverlapInfo.overlap_x`, `OverlapInfo.overlap_volume`,
  `FaceCoordinateSystem.origin`), and `set_absolute_position` takes `x`, `y` and `z`.

## [0.4.0] - 2026-09-10

Every feature-creation tool had been rejected by the Onshape API since mid-2026, and a fresh
install had been broken by `mcp` 2.x. This release makes the server work again. All seven
builders, the new extrude option, and both pattern tools were verified live against
cad.onshape.com on 2026-09-10.

### Fixed

- All seven feature builders (extrude, revolve, fillet, chamfer, linear pattern, circular
  pattern, boolean) send payloads the current Onshape API accepts: the invalid
  `libraryRelationType: "NONE"` field is gone; revolve uses `fullRevolve`/`angle` with an
  explicit `bodyType`; feature patterns use `instanceFunction`, `directionOne` and `axis`;
  boolean is `booleanBodies` with `operationType` values `UNION`/`SUBTRACTION`/`INTERSECTION`
  and `keepTools`. (#25 by @LT-SpArK, fixing #18 reported by @candera; also #19, #20, #24)
- `create_thicken` wraps its payload in `BTFeatureDefinitionCall-1406` like every other
  builder, so it no longer fails with "Could not resolve type id 'BTMFeature-134'". (#25, #24)
- `create_extrude` and `create_thicken` report the real feature ID instead of `unknown`. (#25)
- World Y and Z were swapped in the new revolve/pattern axis helper: a Y axis line was drawn
  on the Front plane (whose vertical is world Z) and the linear-pattern direction faces were
  crossed. (#25 follow-up)
- `create_document` defaults to a public document. Free Onshape accounts reject private ones
  with HTTP 409 "Free accounts only allow access to public documents", so creation had never
  worked on a free account.
- Shaded-view screenshots decode the flat `images` list the API actually returns (the
  OpenAPI schema says list-of-lists) and scale the model to fit the image (`pixelSize=0`). (#30)
- `get_variables` and `set_variable` work against Variable Studios: the API returns
  variable-table groups (each with a `variables` array) rather than a flat list, and
  `setVariables` requires a `type` per entry and replaces the whole table. `set_variable` now
  merges into the existing variables and infers `LENGTH`/`ANGLE`/`ANY` from the expression's
  units. (resolves the defect behind #22 by @candera)

### Added

- `oppositeDirection` on `create_extrude`, mirroring thicken. (#23 by @candera)
- `capture_part_studio_screenshot` and `capture_assembly_screenshot`: render the current
  geometry to PNG, returned inline as an image and optionally saved to disk. Accepts the six
  named views, `iso`, or a raw 12-number view matrix. (#30, originally #27 by @WoodlandTools)
- `reapplyFeatures` on `create_linear_pattern` and `create_circular_pattern` (Onshape's
  "Reapply features"), for when the patterned body was modified by a later fillet, chamfer or
  boolean and the pattern fails with `PATTERN_SWITCH_TO_PER_INSTANCE`.
- Regression test asserting no builder emits `libraryRelationType: "NONE"`. (#29, from #19
  by @candera)
- `create_variable_studio`: create a Variable Studio, whose variables are shared across the
  document and referenced as `#name`.
- `scripts/run-with-creds.sh`: launch the server with credentials decrypted from a gpg file,
  for editor integrations where environment variables are awkward. (from #22 by @candera)

### Changed

- Revolve and circular pattern create a construction-line sketch (`_Axis X`/`Y`/`Z`) through
  the origin and use its edge as the axis, because Onshape exposes no queryable origin axis.
  This adds two API calls per revolve or circular pattern. (#25)
- `mcp` is pinned to `>=1.2,<2`; 2.x removed the low-level server decorators this project
  is built on. Fixes #21. (#28)
- Lint rules are pinned explicitly to `E4, E7, E9, F` so CI no longer changes with each ruff
  release. (#28)
- `uv.lock` refreshed (it had been missing `loguru`); code formatted with `ruff format`;
  `coverage.json` no longer tracked.

### Known gaps

- The batch FeatureScript builders and the constrained-polygon sketch tool on
  `feature/batch-featurescript` are not part of this release.

## [0.3.0] - 2026-03-02

### Added

- Slider and cylindrical mates, mate connectors, and motion limits for revolute, slider and
  cylindrical mates.
- Mate connectors rewritten to use face-based geometry queries.
- `get_body_details` (face IDs, surface types, normals), `get_assembly_features`, and
  `elementId` on `get_assembly`.
- Offset support on the mate tools.
- Assembly workflow guide and cabinet assembly example.

### Fixed

- Limit parameter IDs for slider and revolute mates.
- Body-details case bug.

## [0.2.0] - 2026-02-24

### Added

- Assembly management tools: `create_assembly`, `add_assembly_instance`, `transform_instance`,
  `create_fastened_mate`, `create_revolute_mate`.
- Assembly positioning tools and interference detection.
- Expanded sketch geometry tools: `create_sketch_circle`, `create_sketch_line`,
  `create_sketch_arc`.
- Part Studio feature tools: `create_fillet`, `create_chamfer`, `create_revolve`,
  `create_linear_pattern`, `create_circular_pattern`, `create_boolean`, `delete_feature`.
- FeatureScript tools: `eval_featurescript`, `get_bounding_box`.
- Export tools: `export_part_studio`, `export_assembly`.
- API modules: `AssemblyManager`, `ExportManager`, `FeatureScriptManager`.
- Builders: `BooleanBuilder`, `ChamferBuilder`, `FilletBuilder`, `MateConnectorBuilder`,
  `MateBuilder`, `LinearPatternBuilder`, `CircularPatternBuilder`, `RevolveBuilder`.
- Knowledge base example: parametric bracket walkthrough.

### Fixed

- Occurrence transform API format; full circles drawn as two semicircular arcs; live-testing
  bugs in variables, sketches, search, and POST handling.

## [0.1.0] - 2026-02-20

### Added

- Onshape API client with OAuth and API key authentication
- Document management tools: `list_documents`, `get_document`, `create_document`
- Part Studio tools: `list_part_studios`, `create_part_studio`, `get_features`, `add_feature`
- Assembly tools: `list_assemblies`, `get_assembly_definition`, `add_assembly_instance`, `add_mate_connector`, `add_assembly_mate`
- Auto-load `.env` from package directory
- CI pipeline with multi-OS/Python matrix testing
- 80%+ test coverage requirement

[Unreleased]: https://github.com/hedless/onshape-mcp/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/hedless/onshape-mcp/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/hedless/onshape-mcp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/hedless/onshape-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/hedless/onshape-mcp/releases/tag/v0.1.0
