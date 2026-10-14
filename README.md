# WC-T07: Recovering an Explicit Requirement from Incomplete Conversation History

A small evaluation pilot from DHAIM Lab.

## The observation

A vote-counting task explicitly required a C program to list each invalid vote, not merely count invalid votes. In the original WildChat conversation, the assistant attempted individual reporting in an intermediate revision, but wrote through an output-file pointer before opening the file. A later revision replaced individual entries with a count. After the user said the code was correct and requested aligned scores, the alignment snippet omitted even that standalone reporting line, while retaining the total number of invalid votes elsewhere.

The important distinction is **listing the invalid votes versus reporting their number**. A plausible-looking answer and user approval did not establish that the original requirement had been fulfilled.

We tested whether this incomplete history would carry forward into new model responses, and whether a general reminder would help.

## What we found

**All three tested models produced the individual invalid-vote list in all 15 inherited-history runs. The reminder condition also retained the list in all 15 runs.**

- A, inherited history: list omission **0/15**.
- B, inherited history with a general reminder: list omission **0/15**.

The omission we were looking for did not recur in these continuations. A benefit from the reminder was not demonstrated, because the inherited-history baseline already succeeded. This is a useful negative finding: a requirement problem in an older natural conversation was not reproduced by the tested models under this fixed-history continuation procedure.

## How we tested it

We used one deliberately selected programming case from **allenai/WildChat-1M**:

- **A — Inherited history:** the original nine-message prefix, including incomplete prior assistant work, ending with a request for the full code.
- **B — General reminder:** the same first eight messages, with a designed general reminder replacing the final user message.
- **C — Fresh start:** only the original first user request, without the intervening conversation.

Three models × three conditions × five repetitions produced **45 completed replacement runs**. Every repetition used a fresh conversation and the fixed run order. The generated programs were evaluated using the frozen v0.4 verifier and two primary input fixtures. Later alignment requirements applied to A/B, not C. No scoring rules were changed in response to the results.

## Automatic results

| Recorded model identifier | A: PASS / REVIEW | B: PASS / REVIEW | C: PASS / REVIEW |
|---|---:|---:|---:|
| `openai/gpt-5.6-sol` | 5 / 0 | 5 / 0 | 5 / 0 |
| `anthropic/claude-opus-5@default` | 5 / 0 | 5 / 0 | 5 / 0 |
| `google/gemini-3.7-flash` | 5 / 0 | 5 / 0 | 4 / 1 |

Overall: **44 automatic PASS, one REVIEW_REQUIRED, zero automatic FAIL**.

### Why one result remains REVIEW_REQUIRED

The frozen parser did not recognize a singular winner heading in one fresh-start response. A separate fresh-context review, with model and condition identifiers withheld, accepted the election-result content, the individual invalid-vote list and the winner label on both primary fixtures.

It also identified an interpretation boundary: the program writes election results to the requested file but prints an incidental status message to standard output. If “all output” includes that message, the full output contract is not satisfied; if it refers to election results, it is. **The automatic REVIEW_REQUIRED label remains unchanged.** Metadata masking is not a guarantee against every possible inferential cue. The review row's nullable automatic metrics remain null; they are not silently converted into successes.

## Reproducibility package

The downloadable release contains all 45 unchanged extracted C programs, the byte-identical frozen v0.4 verifier, name-substituted public fixtures, gold values, original result metadata, clearly marked transformed evaluation display records, and offline verification/replay instructions.

An independent release-gate report records **44 PASS and one REVIEW_REQUIRED**, matching the original-fixture scoring run by run and in detail (Python 3.11.15; GCC 13.3.0). The report was supplied to the project; the publication preparer did not independently repeat that replay.

Name substitution is **not anonymization**: the publicly identified source may allow recovery of the original conversation and names. The public replay uses documented derived fixtures, not the exact original input bytes. Programs, verifier and original automatic results remain unchanged.

Download: [WCT07_PUBLIC_REPLAY_RELEASE_v0.1.0_2026-10-14.zip](WCT07_PUBLIC_REPLAY_RELEASE_v0.1.0_2026-10-14.zip). The archive includes its own SHA-256 manifest. It runs offline with Python and GCC in an isolated disposable Linux environment; no new model calls are needed. Read the safety instructions before executing generated code.

See LICENSE_SCOPE.md: project-authored evaluation software is MIT; project-authored documentation and text-free metadata are CC BY 4.0. Generated program artifacts and external source-derived material have separate notices, not a blanket project relicense.

## Costs and archival incident

The replacement execution cost **$2.06784995**. An earlier execution cost **$1.96462345**, but its raw outputs were not durably exported before a Kaggle session reset. Those missing outputs are not reconstructed or combined with the replacement dataset. Each complete replacement checkpoint was preserved locally before the next call.

Total recorded model-call expenditure was **$4.03247340**; human effort is not included.

## Limitations

This is one selected case, five repetitions per model–condition cell and two primary fixtures—not a representative sample or a general model ranking. It tests continuation from inherited fixed history, not repair of a model's own live conversation. The recorded identifiers do not establish unobserved backend versions, and the study is not a controlled historical-versus-current model comparison. It does not establish equivalence between conditions, broad correctness, or commercial value.

Instrument version: **0.4**. Public release version: **0.1.0**.

Name substitution is not anonymization: the publicly identified source may allow recovery of the original names and conversation.

## Project links

- [GitHub repository](https://github.com/dhaim-lab/DHAIM)
- [Hugging Face results dataset](https://huggingface.co/datasets/dhaim-lab/dhaim-wct07-pilot-results)
