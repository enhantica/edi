# Clean notebook and official-address gates

Supply `EDI_TUTORIAL_WHEEL` with the actual wheel produced for the selected platform.
`EDI_TUTORIAL_WHEELHOUSE` contains only the offline Jupyter kernel/nbclient dependency
wheels and the wheel's declared dependencies; it must not contain another edi wheel.
Preparation can resolve those packages before the acceptance run. The run itself
has no package-index network access and does not install extra scientific helpers.

Each original notebook retains its install cell. A fresh venv first receives only
`ipykernel` and `nbclient`, then that cell installs the selected wheel through an
offline find-links directory. The wheel's dependencies are installed by pip from
its actual METADATA. Private prefix and import-origin witnesses surround the
unchanged cells. A private kernel spec selects that venv's isolated interpreter.
No source overlay, user site, host site-packages, or `EDI_SOURCE_BUILD` escape is
allowed. A deliberate missing import must fail in the kernel and propagate.

Set `EDI_TUTORIAL_COLLECTION` to the real local collection producer's output, or
the gate runs that producer itself. Only the collection transport is local: no
model, fit, chart or table result is replaced. Saved execution notebooks, source
hashes, package lists and failures remain in pytest's artifact directory. Each
case's private venv is deleted afterwards. Declared missing notebooks fail too.

Official docs links map to the actual freshly built user site. Other service
artifacts can be provided with `EDI_TUTORIAL_DOWNLOAD_ROOT` (default
`build/publish-tree`), `EDI_TUTORIAL_APP_ROOT` (`build/wasm/site`) and
`EDI_TUTORIAL_CONTRIBUTOR_ROOT` (`site/dev`). An absent artifact, missing target,
missing anchor or escaping path fails; GitHub sources and scientific references
remain external. These mappings never rewrite the published page text.

Release qualification uses a wheel produced with the pinned release SDK. A local
consumer-extension repack is diagnostic evidence only; a fresh Python environment
does not by itself certify the native shared-library closure or hosted CI.
