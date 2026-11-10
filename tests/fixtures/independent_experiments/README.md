# Independent experiments: mathematical and isolated controls

Three P1 Ni structures each own a different measured dataset and one free occupancy.
The structure and experiment orders disagree; atom IDs deliberately repeat across
structures. Noise, point counts and optima differ, so pooled uncertainties fail.

`reference.py` writes every input, including the app project, without importing either
product. The Sears Ni scattering length is 10.3 fm, also frozen by the existing
single-crystal external reference. The weighted normal equation solves occupancy
squared and its local Fisher derivative gives its standard uncertainty. Each combined
fit is additionally compared with a fresh, isolated single-experiment fit from the
same inputs. No engine answer is an absolute correctness reference or a fixture pin.

The one-structure joint control has a different, pooled weighted solution. The scan
control has zero fixed diffraction scale and one free constant background; independent
and sequential scans must keep their ordinary CSV/events and weighted-mean results.
