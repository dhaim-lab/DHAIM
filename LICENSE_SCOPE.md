# File-level license scope

This is a mixed-material research package. There is no blanket license over
every file, and no external dataset or provider output is silently relicensed.

## MIT — project-authored evaluation software

LICENSE_CODE_MIT.txt applies to verifier.py, verify_package.py and
rescore_saved_programs.py, to the extent of project-held rights. Licensing
notices are separate so the frozen verifier bytes remain unchanged.

## CC BY 4.0 — project documentation and text-free research metadata

LICENSE_DOCS_DATA_CC_BY_4_0.txt applies to README.md, LICENSE_SCOPE.md,
project-authored explanatory text in docs/, data/runs.jsonl,
program_index.json, FIXTURE_PROVENANCE.json, ORIGINAL_EVALUATION_PROVENANCE.json,
PRIVACY_PRECHECK.json and SHA256_MANIFEST.json, to the extent of project-held
rights. Rights in bare facts may not require permission. Attribution:
DHAIM Lab, WC-T07 release 0.1.0 (2026). Third-party notices and standard
license texts are not claimed as project-authored work.

## Generated programs — output-artifact notice, not blanket MIT

programs/*.c are unchanged model-generated evaluation artifacts, not claimed
as human-authored code. See GENERATED_OUTPUTS_NOTICE.txt. Neither of the two
project licenses above is applied to these files. Do not infer that this
package grants rights in third-party code or removes provider restrictions.

## Source-derived fixtures and evaluation display records

votes*.txt, derived_gold/*.json and
original_evaluations_name_substituted/*.json retain a separate source/output
boundary. See THIRD_PARTY_SOURCE_NOTICE.txt and GENERATED_OUTPUTS_NOTICE.txt.
No project-wide MIT or CC BY relicense is asserted over their external
contents. Numerical facts are distinguished from any protectable expression.

The public fixtures are named substitutions; the original private fixtures
and output records remain unchanged. Substitution is not anonymization.
