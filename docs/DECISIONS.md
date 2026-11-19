# Design decisions

1. **CSV in git as source of truth** (not a server database): reviewable diffs, PR-based review, no hosting, reproducible builds. SQLite is a build product for querying/QGIS.
2. **Live database scope.** The live database currently contains 11 verified Ridgecrest observations for the foreshock and mainshock. The unverified v7 prototype is not retained in the repository.
3. **No derived high-level metrics.** OFD/SSD are ingested only as published %; the v7 *absolute* OFD/SSD metrics were removed from scope (2 v7 records dropped, listed in the ledger).
4. **Uncertainty as positive offsets + a type**, converted to absolute bounds only in the build. v7 mixed both conventions.
5. **Range / qualifier / digitization are first-class columns**, so no number is ever invented from them.
6. **Static interfaces with one shared `data.js`** (no framework, no bundler): works from `file://` and GitHub Pages; pages cannot diverge because they share `common.js`.
7. **Pull request = staging + approval.** The importer is all-or-nothing with rollback; a separate staging layer was judged unnecessary at this scale (see Phase 2 in ARCHITECTURE.md).
8. **One-sheet workbook.** The contributor sheet mirrors the field dictionary the project owner wrote (Identification / Value / Uncertainty / Location / Method). Series are expressed with `observation_group_id` instead of separate array sheets; the importer maps this onto the observations/arrays tables. Deviations from the original field list: `uncertainty_minus/plus` (positive offsets) instead of `uncertainty_lower/upper` (which were ambiguous between offsets and bounds), no contributor-entered `database_derived`, ranges have their own columns, events only (`target_type` dropped for phase 1), new context fields are optional.
9. **No regression line** in the correlation page yet (explicit user decision).

## Ideas taken from the ChatGPT foundation
Empty-by-default database with archived prototype data kept outside the repository; contributor workbook with dropdowns and provenance columns; deployment through GitHub Pages and Actions; branch + PR delivery with a safe stop when authentication is missing; explicit alias/dedup rules; separation of ranges, scientific uncertainty and digitization uncertainty.
## Ideas deliberately not taken
A TypeScript/Vite stack and a CLI package (adds a toolchain contributors do not need; Python scripts + static HTML are enough); a separate staging/promotion layer (see 7).

## Open curation items
No additional prototype curation queue is retained in the repository. Future event and source additions will be driven by contributor ingestion workbooks and live validation.

## 2026-11-19 — Ingestion phase decisions

1. **Scope of this database for now:** only published values: single reported values (e.g. Mw, mapped rupture length, depths, mechanism) and published minimum, mean, median and maximum, each with its published uncertainty, uncertainty type and sample count. No arrays: along-strike series and individual measurements are stored in the 3D database. No values derived from raw data and no figure digitization in this phase; derived metrics may be added in a later phase as a clearly separate category.
2. **Exception:** `surface_rupture_discontinuity` may be derived from a published `surface_rupture_span` and a published `mapped_surface_rupture_length` from the same study, flagged as derived.
3. **Ingestion order:** event by event (starting with the 2019 Ridgecrest foreshock `Ridgecrest 1` and mainshock `Ridgecrest 2`, grouped under `Ridgecrest sequence`), paper by paper, entering every metric each paper reports. Only whole-rupture values for each event; per-segment values are not entered for now.
4. **Metric meanings:**
   - `total_surface_displacement` = displacement envelope across the whole deformation zone.
   - `surface_fault_slip` = slip offsets measured on surface fault ruptures (localized slip).
   - Diffuse deformation (e.g. Antoine et al., 2021) is entered under `off_fault_deformation_fraction` / `off_fault_deformation_absolute`, with its definition in `method_details`; differences between definitions are visible in the study-to-study comparison.
5. **Vertical motion:** vertical offsets across a fault are entered with the existing component `vertical/throw (source code T)`. Uplift or subsidence of a single block (not an offset across a fault) is not entered. No new components.
6. **Uncertainty:** a published ± whose convention is not stated in the paper is entered as `unspecified`, with the most likely interpretation explained in `uncertainty_description`.
7. **New metrics:** `off_fault_deformation_absolute` and `ssd_absolute` added (definitions from the v7 prototype).
