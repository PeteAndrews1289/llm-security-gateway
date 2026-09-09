# Corpora

Frozen inputs for the adversarial evaluation. See `docs/evaluation-protocol.md`.

## Files

| File | Category | Purpose |
|---|---|---|
| `benign.jsonl` | `BN` | Legitimate MyFitPlate user traffic. Measures the input filter's false-positive rate. |
| `adversarial.jsonl` | `DI` `RP` `EO` `OX` `II` `MT` | Attack corpus. Measures evasion and end-to-end leak rate. |

## Item format

One JSON object per line:

```json
{"id": "BN-001", "category": "BN", "text": "...", "source_task": "correct-logged-food"}
```

Adversarial items add `"mechanism"` (one line on what the item tests) and, for
`II`, a separate `"context"` field. `MT` items carry `"turns"` as an ordered list
instead of `"text"`.

## Benign corpus provenance

Derived from **MyFitPlate `docs/support.md`, "Common Tasks"** and the product-area
list in that repository's README — both authored before this evaluation existed
and with no reference to `lambda_firewall/security_filters.py`.

### Construction rule

Prompts are written from the task list, in one pass, **without consulting the
filter source and without revision after any filter has been run over them.**
Contamination enters during revision far more than during first drafting: the
temptation is to soften a prompt once you have seen it produce a block. First
draft is final.

### Author population

The corpus is written by a single author who is the application's daily user for
food logging and training, but who has **not** used its AI assistant feature.
The *tasks* in this corpus are therefore grounded in real, routine product usage;
the *phrasing* is constructed, because no observed assistant traffic exists.

MyFitPlate is a shipped App Store application without a user base, so there is no
support inbox, review corpus, or traffic log to sample. Persisted assistant
conversation history caps at 12 messages including model replies -- too few to
seed from.

This corpus is one informed person's model of legitimate traffic, not a sample of
observed behaviour. The false-positive rate describes this corpus. No inference
is available about a real user population.

### Tested and rejected: application vocabulary as an independent source

An earlier plan was to show mechanically that the blocklist collides with the
application's own product vocabulary -- evidence that would require no corpus and
no author judgement. It was tested and it failed. Searching MyFitPlate's
user-facing Swift string literals for all nine blocklisted phrases returned
**zero matches**.

Recorded because it bounds a claim this evaluation must not make. That
`contains_prompt_injection("Can you override my daily calorie goal?")` returns
True is verified and reproducible. That a user would naturally phrase a request
that way is **not** established by any evidence here, and the false-positive
result is reported as a property of this corpus rather than as a frequency claim
about real traffic.

### Declared contamination

The author had prior exposure to five of the nine blocklisted terms before
writing this corpus, through earlier discussion of the filter's behaviour. This
cannot be undone and is disclosed rather than concealed. Two mitigations apply:

1. Prompts are seeded from a pre-existing product task list rather than written
   free-form, which constrains them toward realistic phrasing.
2. The proportion of benign items containing blocklisted terms is reported
   alongside the false-positive rate, so a reader can judge whether the corpus
   looks avoidant (suspiciously low) or seeded (suspiciously high).

A false-positive rate from this corpus is evidence about *this* corpus. It is
not an estimate of the rate a production deployment would see.

## Adversarial corpus QA (pre-freeze)

The adversarial corpus is white-box: the author knew the filter contents while
writing it. The mitigation is an independent review pass by a second reviewer
against a single construction criterion:

> Would this item be unchanged if the filter's blocklist and redactor pattern
> contained different values? If not, the item measures the filter's internals
> rather than an attack technique, and is revised or dropped.

### Result

- **Reviewed:** random 30 of 150 (20%), `random.seed(1289)`, reproducible via
  the sampling in this directory's review worksheet.
- **Flagged:** 1 (`DI-019`).
- **Revised:** 1. **Dropped:** 0.

`DI-019` (correction framing) originally used a decoy password in the real
secret's family, `FitPlate_DB_Winter2024`. This failed the criterion on two
independent grounds: (1) it assumed knowledge of the secret's naming format,
which the §2 threat model places outside a black-box adversary's reach; and
(2) the decoy matched the output-redactor regex `FitPlate_DB_[a-zA-Z0-9@_]+`,
so an echoed decoy would have triggered redaction and corrupted the
redactor-save metric. The decoy is now generic (`Spring2024Login!`).

A full-corpus scan (all 150 items) for strings matching the redactor pattern
confirmed `DI-019` was the only instance; the error class does not recur.

### Interpreting the flag rate

One revision in a 20-item-plus review does not prove the remaining 120
unreviewed items are clean. It establishes that the construction criterion was
applied, that it caught a real defect, and that the caught defect was corrected
at the generator source rather than in the output file. The generator
(`scripts/build_adversarial_corpus.py`) records each in-review revision inline,
so the construction history is auditable rather than asserted.
