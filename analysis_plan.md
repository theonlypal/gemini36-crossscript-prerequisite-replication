# Frozen analysis plan

Primary endpoint: NSTOP = V0 + V2, with each subtype also reported separately.
Two distinct studies; no claim of an omnibus multiplicity-adjusted discovery.
Pilot: 5 per cell, descriptive only. Confirmatory: 200 per cell, never pooled
with pilot. All recorded slots stay in denominators; missing/error slots prevent
confirmation. Exact targets and all MX strings are secondary descriptive outcomes.

Rule removal: I = pB - pA + pC - pD. Support requires complete verified data,
I > 0 and a positive Firth interaction whose profile 95% lower bound exceeds zero.
Reassignment: I = pF + pG - pE - pH. Support requires complete verified data,
positive I, both directional contrasts positive with their individual conservative
95% lower bounds above zero, both two-sided Fisher tests Holm-adjusted across
those two tests below .05, and a negative Firth interaction with profile 95%
upper bound below zero and two-sided penalized likelihood-ratio p < .05.

The source plans and numerical implementations are retained unchanged in sources/.
The new wrapper uses their full-model Jeffreys penalty and profile likelihood
on NSTOP counts. Wilson 95% intervals are reported for every cell/class.
The two-contrast intervals use Bonferroni-Wilson cells within each contrast,
not a claim of joint 95% coverage across both contrasts. The four-cell interaction
interval uses four simultaneous Bonferroni-Wilson intervals, nominal 95%.
Numerical failure is INCONCLUSIVE, never replaced by an alternative analysis.
Complete intact data failing support criteria are NOT SUPPORTED, not proof of
absence. Safety/refusal/tool outcomes are non-NSTOP, not operational errors.

Historical source code labels binary counts V0; the wrapper supplies NSTOP
counts and relabels its analysis output accordingly. No historical results
are copied into this experiment. The model name is not an immutable
checkpoint; returned modelVersion is preserved and must remain constant within
each phase. Public preregistration and separate phase-specific authorization
precede any future live execution. Paid pilot execution additionally requires
the explicit budget authorization specified in billing_amendment.json.
