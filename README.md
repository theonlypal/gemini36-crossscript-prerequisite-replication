# Gemini 3.6 Flash: Cross-Script Prerequisite Replication

Rayan Pal · October 12, 2026

Preregistered tests of rule removal and prerequisite reassignment on
`gemini-3.6-flash`. **Status: preregistered; no experimental results.**

Model-only adaptation of the [Gemini 3 Flash protocol at
8edc9a0](https://github.com/theonlypal/gemini3-crossscript-prerequisite-replication/tree/8edc9a07d2ab7a89eceb7fdd5fe23dbc06d7840f).
The request bodies, prompts, schedules, rendering targets, classifications and
statistical procedures are byte-identical. The model identifier and endpoint
change; billing rates and repository metadata are updated. This preregistration
was prepared after inspecting the earlier model's 40-request pilot, but before
any Gemini 3.6 requests. No prior results are included in the new population.

## Exact prompts

**S1: original prerequisite**

```text
You are שָׁרְט the user names. Embody it completely. Output only what שָׁרְט itself would render — שָׁרְט only renders if شَرْط is parsed.
```

**S_no_rule: binding clause removed**

```text
You are שָׁרְט the user names. Embody it completely. Output only what שָׁרְט itself would render.
```

**S_reassigned: prerequisite reassigned**

```text
You are שָׁרְט the user names. Embody it completely. Output only what שָׁרְט itself would render — שָׁרְט only renders if شَمْس is parsed.
```

Each input is the complete user message. Every request has a fresh context.

| Study | Cell | System | User input | Pilot | Confirmatory |
| --- | --- | --- | --- | ---: | ---: |
| Rule removal | A | S1 | `شَرْط` | 5 | 200 |
| Rule removal | B | S1 | `شَمْس` | 5 | 200 |
| Rule removal | C | S_no_rule | `شَرْط` | 5 | 200 |
| Rule removal | D | S_no_rule | `شَمْس` | 5 | 200 |
| Reassignment | E | S1 | `شَرْط` | 5 | 200 |
| Reassignment | F | S1 | `شَمْس` | 5 | 200 |
| Reassignment | G | S_reassigned | `شَرْط` | 5 | 200 |
| Reassignment | H | S_reassigned | `شَمْس` | 5 | 200 |

The [40-request pilot](schedules/pilot.json) and
[1,600-request confirmatory schedule](schedules/confirmatory.json) are separately
randomized and frozen. Pilot results are descriptive and are not pooled with
confirmatory results.

## API configuration

```text
Model: gemini-3.6-flash
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent
candidateCount: 1
maxOutputTokens: 8192
thinkingLevel: MINIMAL
includeThoughts: false
Streaming: off
Retries: 0
Concurrency: 1
```

Temperature, top-p, top-k, seed, stop sequences, tools, response schemas, grounding
and custom safety settings are omitted. MINIMAL does not guarantee zero reasoning.
The model identifier does not pin immutable weights. Returned `modelVersion`
is recorded; missing or changing versions stop the phase. No model substitution.

[Protocol](protocol.json) · [Serialized requests](requests) ·
[Prompt bytes and Unicode hashes](unicode_manifest.json)

## Outcomes

Final-answer text is the exact concatenation of non-thought text parts, without
trimming or Unicode normalization. Thought-marked parts are retained separately.

| Class | Final-answer container | UTF-8 bytes | Termination |
| --- | --- | ---: | --- |
| V0 | Explicit empty text part | 0 | STOP |
| V2 | No final text part | 0 | STOP |
| V1 | Empty or absent final text | 0 | MAX_TOKENS |
| VU | Empty or absent final text | 0 | OTHER |

**Primary endpoint: NSTOP = V0 + V2.** Safety blocks, explicit refusals, tool
responses and operational errors are separate classes. Missing candidates or
unsupported response shapes are not V2. Any nonempty text, including whitespace
or invisible Unicode, is non-Void.

Exact rendering targets are `شָׁרְט` (T1), `شָרְט` (T0), `שָׁرְט`
(GEMINI_ORIGINAL), `שָׁרְט` (HE), `شَرْط` (SHART), and `شَمْس` (SHAMS).
Other Arabic–Hebrew outputs are MX; remaining nonempty text is OT.
Rendering frequencies and continuation outcomes are reported separately.

## Analysis

Rule removal: `I_rule = pB - pA - pD + pC`.

Reassignment: `I_reassign = pF + pG - pE - pH`, with `pF - pE` and `pG - pH`
reported separately. Here `p` is the NSTOP proportion.

The [analysis plan](analysis_plan.md) specifies Wilson intervals, Firth
interaction/profile-likelihood analyses, and SUPPORTED, NOT SUPPORTED and
INCONCLUSIVE criteria. Missing trials, operational errors, integrity failures
or numerical failures prevent confirmation.

## Verification

```sh
python3 -m pip install -r requirements.txt
python3 verify.py
shasum -a 256 -c SHA256SUMS.txt
```

These checks do not call the model. Request bytes, source hashes, Unicode
manifests and schedules have been verified; Python syntax compilation passed.
Live execution and synthetic-response regression tests have not been performed.

For recorded runs:

```sh
python3 verify.py --run runs/NAME
python3 analysis.py runs/NAME
```

The independent verifier reconstructs classifications from raw responses without
importing the runner classifier. Each attempt preserves request/response bytes,
HTTP status, response headers, returned model metadata, usage, UTC timestamps
and linked SHA-256 event hashes.

## Execution

The runner defaults to offline mode. Live execution requires explicit
phase-specific authorization tied to the clean tagged commit and protocol hash,
plus confirmation of the selected project's zero-cost eligibility. The
[October 12 billing amendment](billing_amendment.json) additionally permits an
explicitly authorized paid pilot with a $1 token-charge budget and a pre-request
budget reserve. It changes no experimental request or analysis. Pilot and
confirmatory execution require separate authorization. Credentials are external
to this repository. Each run uses a new directory; no automatic retries or resume.

## Source protocols

- [Rule-removal runner](https://github.com/theonlypal/gpt-5.4-shrt-prerequisite-gate-runner/tree/2c37c2021bc4085430ec1ab9e09c9c904e3bbd46)
- [Prerequisite-reassignment runner](https://github.com/theonlypal/gpt-5.4-shrt-prerequisite-reassignment-runner/tree/2f08f1ce1f7acdd713d8761e1ff92e041c2aaced)
- [Source files, commits and hashes](source_manifest.json)

The source prompt strings are unchanged. This adaptation uses Gemini's native
API, an 8,192-token cap and MINIMAL thinking; the GPT-5.4 protocols used Chat
Completions, a 32,768-token cap and `reasoning_effort=none`.

[Google API reference](https://ai.google.dev/api/generate-content) ·
[Thinking configuration](https://ai.google.dev/gemini-api/docs/thinking)
