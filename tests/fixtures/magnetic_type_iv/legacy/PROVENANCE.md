# Legacy editor regression pins

These are regression pins, not scientific references. `generate_inputs.py` writes
invented non-table type I and III structures. Compile `generate.cpp` with the
immutable edi `499909374` and crysta `8453a08e9` SDK headers and libraries, then run
it with this fixture directory and a new scratch output directory. The observations
cover native load and save, deterministic new-atom defaults, FullProf export, and
reimport of the exported PCR. A baseline refusal is recorded explicitly.

PCR comments and the temporary export-directory prefix are excluded from the
regression observation. Every exported data row remains byte compared.
