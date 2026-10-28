# Benchmark Dataset TODO

## Completed
- [x] Research public data sources for paired bodycam + police reports
- [x] Identify best source: OCDA OIS reports (18 verified paired cases)
- [x] Identify secondary source: American Fork PD on Internet Archive
- [x] Design benchmark directory structure
- [x] Write annotation JSON schema (claim types, discrepancy types, evidence refs)
- [x] Write manifest JSON schema (URLs, hashes, metadata)
- [x] Write download script (scripts/download.py)
- [x] Write validation script (scripts/validate.py)
- [x] Write incident report template (schema/report_template.txt)
- [x] Write benchmark README

## Next: Populate manifest with verified cases
- [x] Download OCDA PDFs, verify URLs still work (16/18 alive; Hernandez + Nava 404'd, dropped)
- [x] Grab YouTube and Internet Archive URLs for each video (16/16 YT alive, 10 IA mirrors verified)
- [x] Compute SHA-256 hashes for all files (16 PDFs + 10 IA videos; 6 YT-only need cookies)
- [x] Populate manifest.json with all sources (32 entries: 16 PDFs + 16 videos)
- [x] Add yt-dlp support to download.py for age-restricted YouTube videos
- [ ] Test download.py end-to-end (fresh download from empty evidence/)

## Next: Create annotations
- [x] Write fictional incident reports per scenario (15 scenarios from DA letters)
- [x] Create ground-truth annotation JSON for each scenario (220 claims total)
- [x] Validate all annotations against schema
- [ ] Add video timestamps (start_seconds/end_seconds) to evidence_references
- [ ] Verify claims against actual bodycam video (spot-check discrepancies)
- Note: SC-008 (Tice) skipped — PDF was a press release, not an investigation letter

## Next: Pipeline & Evaluation
- [x] Build evaluation runner (precision, recall, F1, IoU, stratified breakdowns)
- [x] Define prediction schema
- [x] Build pipeline scaffold (extract → retrieve → verify)
- [x] Implement Claude adapter
- [x] Implement Nemotron adapter (stub)
- [x] Implement single-pass baseline
- [ ] Run claim-first pipeline on one scenario (needs ANTHROPIC_API_KEY)
- [ ] Run single-pass baseline on one scenario
- [ ] Compare baselines and get first metrics
- [x] Research Nemotron Omni capabilities and API format (video+audio+text confirmed, 2-min video limit)
- [x] Implement Nemotron adapter (OpenAI-compatible, vLLM, video clip extraction)
- [ ] Implement transcript-only baseline

## Later: Expand benchmark
- [ ] Add American Fork PD scenarios
- [ ] Write synthetic reports for additional discrepancy types
- [ ] Add negative examples (fully consistent reports)
- [ ] Add ambiguous/missing evidence scenarios
