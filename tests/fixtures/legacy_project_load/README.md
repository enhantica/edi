# Project-load boundary fixtures

All committed projects use the current schema and declared background row ids.
Run `python3 generate.py` to copy the independent loop-identity fixtures and add
assigned start values `1.25 + index * 0.375` and uncertainties `0.03125 * (index + 1)`.
The values are closed-form constants; no fit supplies them. The Python load gates
introduce old saved-slot names in disposable copies and require a short refusal
naming the offending spelling. The Qt actors do the same at the real Session load
boundary. The incomplete current-schema project exercises failed-load routes and
archive pack/unpack; it contains no structure files. No owner data is included.
