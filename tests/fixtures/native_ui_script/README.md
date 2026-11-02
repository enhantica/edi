# Native UI wiring transport

The merged native presentation migration moved procedures from QML into the
real `ApplicationInfo` singleton. The existing wiring vectors continue to
execute their actual QML bindings, with their original independently supplied
values and expected results. They now use `edi_app_tests` when the binding calls
native code; ordinary JavaScript still runs in the pinned Node interpreter.

`prepare_script.cjs` uses Node's bundled Acorn parser only to expose the original
lexical fixture variables, `this` and named `with` scopes to Qt. It supplies no
application procedure. The test-only QObject in
`tests/unit/app/test_e11_t5_native_script_fixture.cpp` owns those bindings and a
real QML caller scope. Unknown inputs and missing/stale native runners fail.
The native singleton and its enum values are the real app objects. Fixtures may
provide input owners, callbacks and environment bindings; no expected business
result comes from this transport.

`report_projection.py` reads the JSON embedded by the actual public HTML writer,
rather than inventing browser camera or layout fields in a partial DTO. The
committed schema seed supplies only omitted schema fields. Authored arrays and
scientific fields take priority. Renderer assertions still use independent
numeric and physical convention values.

A core-only CI job must supply the matching app-test artifact through
`EDI_APP_TEST_RUNNER`; the fixture never skips or substitutes an implementation.
Under GitHub Actions it additionally requires the runner's clean build marker
to match `GITHUB_SHA`. The QML fixture is explicitly selected by the transport
and is not part of the default app-test input directory. A no-op vector can
legitimately invoke no native method; every vector must publish exactly one
original observer output without an exception.
