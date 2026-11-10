# Parameter notation controls

Owner record 7dea80601 defines the magnitude interval and three significant
scientific digits. `reference.py` uses Decimal and the existing independently
authored IUCr arithmetic; it imports no product. Values are literal boundary
inputs, not fitted results or regression pins. SU-bearing values retain the IUCr
last place, with value and uncertainty expressed in the same power.

The report witnesses load a small declared P1 project, set literal values,
uncertainties and starts through the public API, then render it without fitting.
The QML witness observes the actual app singleton with real empty projects under
both uncertainty rules. It does not provide a replacement formatter.

`native/CMakeLists.txt` builds only the two existing native formatting case files
against an explicitly supplied product-core archive and its matching crysta SDK.
It is a local scoped producer; the ordinary C++ test target also collects those
same cases. Build with -j 4 under the shared local build lock.
