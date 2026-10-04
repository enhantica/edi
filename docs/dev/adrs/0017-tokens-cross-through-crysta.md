# 0017. Tokens cross into crysta through crysta's own converter

- **Status:** Accepted
- **Date:** 2026-10-01
- **Implementation:** ✅ Implemented —: every vocabulary token `core/src/adapter.cpp` hands crysta goes through
  `crysta::model_token_from_file`; the absorption vocabulary and its registry mapping are asked of crysta; the
  engine's work counters and the model dump are carried for the parity checks
- **Priority:** High
- **Forward constraint (binding on new features):** a new token field crosses the adapter only through crysta's
  converter. edi holds and shows the file's spelling and builds no crysta model token itself; it keeps no list of
  a crysta vocabulary and no mapping between its two spellings.

## Context

edi builds a fresh crysta project for every calculation, fit and save (ADR-0003, ADR-0016 as amended). Its adapter
copied each token of the experiment into crysta's model as edi spells it, which is as the file spells it.

That was right while the file spelling and crysta's model token were the same word. crysta then gave the Hewat
cylinder one registry token, `cylinder-hewat`, in both beam modes, while a TOF file keeps
`cylinder`. crysta's loader converts; edi's adapter did not. crysta's reflection-folding predicate accepts only the
registry tokens, so every TOF project with cylinder absorption computed unfolded inside edi: the same numbers, at
about four times the engine time. Nothing failed, because every gate compares values.

The owner's rule: *"Edi should only pass and get from edi."*

## Decision

1. **One converter, and it is crysta's.** Every vocabulary token the adapter hands crysta — the peak type, the beam
   mode, the radiation probe, the sample form, the scattering type, the absorption type, the three scattering-source
   selectors, a site's `adp_type` and the fitting mode — goes through `crysta::model_token_from_file`, on the
   calculate path and on the delegated save alike. crysta's table maps the spelling to its model token and refuses
   one the experiment's beam mode does not admit.
2. **Resolved identifiers use crysta's resolvers.** The space group is selected by
   `crysta::space_group_from_file`, the rule crysta's own loader applies. Element symbols, Wyckoff letters, descent
   ids and the preferred-orientation link already resolve in crysta and already refuse.
3. **edi holds the file's spelling.** A TOF experiment's absorption type is `cylinder` in edi's model, its Python
   surface and its files. Where edi needs crysta's registry token — the Python class lookup — it asks the adapter
   (`absorption_registry_token`). Where a caller hands edi the registry token, the adapter maps it back
   (`absorption_file_token`). The vocabulary lists in edi's setter are crysta's (`absorption_file_tokens`).
   A peak type registered at run time (`PeakFactory.register`) is registered with crysta's peak registry in the
   same call (`register_engine_peak_type`), because that registry is the vocabulary the crossing reads; it computes
   with its family's base profile, as it did.
4. **The absorption parameters follow crysta's resolved form.** Which coefficients cross (the ABSCOR pair on
   time-of-flight, `mu_r` at constant wavelength) is decided by `crysta::absorption_form_of` on the converted
   token, not by comparing spellings.
5. **Work is counted, and carried.** A fit result carries crysta's work counters verbatim: per bank whether its
   reflection sum ran folded, and the number of reflection structure factors the solve evaluated. They are private
   Python members named as crysta's are (`_folded`, `_structure_factor_evaluations`).
6. **The model can be compared.** `edi._model_dump(project)` is crysta's own dump of the engine project a
   calculation builds, in model tokens. A saved file cannot show a token crossing, because crysta's writer maps a
   model token back to its file spelling. `edi._folds_reflections(project)` and
   `edi._structure_factor_evaluations()` are crysta's fold resolution and work counter.

## Consequences

- A spelling crysta does not admit for the experiment's beam mode now refuses at the crossing, with crysta's
  message, where it used to be copied and computed.
- crysta refuses an unknown model token at every calculation and save. An edi that copied tokens would fail
  loudly, so this class cannot return silently.
- edi's own `.edi` reader keeps validating the file grammar it reads. That is edi's file plane, not a crysta model
  token.
- The parity checks (crysta's Python package against edi, per CLI project) compare the model dumps, the fit
  results and the work counters. A timing ratio is reported and does not gate.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Map `cylinder` to `cylinder-hewat` at the two adapter sites | Rejected: it fixes one token of a class. The next registry token that differs from its file spelling would repeat the defect. |
| Make crysta's folding predicate accept the file spelling | Rejected: two spellings of one model token is the defect, moved into crysta. |
| Compare saved projects in the parity checks | Rejected: the writer maps the model token back, so the two saves are byte-identical with the defect present. |
| A timing gate | Deferred to a reported ratio: counters are deterministic and timings are not. |
