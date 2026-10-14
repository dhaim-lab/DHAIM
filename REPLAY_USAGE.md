# WC-T07 public replay package — documentation release 0.1.1

This package documents the publicly released WC-T07 pilot. Version 0.1.1 is a documentation-only update to published version 0.1.0. Original instrument v0.4 and all original run results are unchanged.

## What is included

45 exact extracted C programs; the byte-identical frozen verifier; text-free original results; name-substituted public primary fixtures; unchanged already-synthetic diagnostic fixture where applicable; numerical gold, provenance/hashes; metadata-masked review findings; original evaluation records with name substitution clearly marked.

No complete model responses, source conversation, secrets, private contact details, or original names are included.

## First: verify without executing generated programs

Unzip into an empty folder. Requires Python 3.10+.

    python verify_package.py

This checks the exact file set, hashes, program count, and byte identity of all 45 programs.

## Independent offline replay

Use an isolated disposable Linux environment with Python 3.10+ and GCC. No pip packages are required. No model calls are made. Do not run generated C on a personal machine with access to secrets. Disable network and do not mount personal folders. Resource limits inside the frozen verifier are not a security sandbox.

From this package directory:

    python rescore_saved_programs.py --execute-reviewed-code --output /tmp/wct07_public_replay.json

Keep output outside the package so strict file-set verification remains valid. Use a fresh output filename each time.

Expected ORIGINAL labels: 44 PASS, 1 REVIEW_REQUIRED. The script compares each run ID individually, not just counts. The independent release-gate report supplied by the project owner records 44 PASS and 1 REVIEW_REQUIRED on these public fixtures, matching every run and the detailed original-fixture scoring. Environment: Python 3.11.15, GCC 13.3.0. This preparer has not independently rerun that computation; see docs/RELEASE_GATE_RECORD.json. Inspect stdout/stderr and list/alignment diagnostics too. If a label differs, record CHANGES_REQUIRED and do not adjust the verifier to force agreement.

## What changed, and what did not

Programs and verifier are unchanged. Original result rows/statuses are unchanged. Only candidate labels in public derived fixtures and display copies of old evaluations were replaced. Label lengths and word boundaries, vote tokens, invalid values, counts, scores and winner identities by candidate position are preserved. The reported release-gate replay matched the retained original-fixture scoring for these 45 programs; this is not a general equivalence proof for arbitrary programs or inputs.

Derived fixture filenames preserve the frozen verifier's expected paths, but hashes and FIXTURE_PROVENANCE.json explicitly distinguish them from originals. Original frozen files are kept privately and were not edited. The public replay is not an exact-byte rerun of the original input fixtures.

The already-synthetic hidden_2 diagnostic uses different vote data; its old success alone does not establish equivalent primary replay.

## Privacy boundary

Name substitution is **not anonymization**. Source identifiers and a public source dataset remain available, so readers may recover the original conversation and names. The substitution avoids directly republishing those names in this package; it does not make the case unlinkable or anonymous. A negative pattern scan is not a guarantee against all identifying information.

## Verification record

Return PASS or CHANGES_REQUIRED, exact ZIP SHA256, environment/GCC/Python versions, manifest verification evidence, 45 per-run replay results, status comparison, and privacy/security scan findings. No new model calls or design changes. Review this archive only; do not rely on private files.

See docs/TERMS_AND_ATTRIBUTION.md and docs/PUBLIC_INTRO_PROPOSAL.md. See LICENSE_SCOPE.md for the exact file-level licensing scope. Version 0.1.0 was published at https://github.com/dhaim-lab/DHAIM and https://huggingface.co/datasets/dhaim-lab/dhaim-wct07-pilot-results. The prior archive and commit history remain available.
