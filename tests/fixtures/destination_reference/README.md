# Download destination reference

An index identifies files; it does not grant authority to name output outside the requested
destination. A listing number only selects an index entry and grants no additional authority.
Safe archive members cannot repair an unsafe extraction root.

The fixture authors its archive bytes, data, SHA-256 values and a distinct outside sentinel.
Its project archive contains a minimal project document and an unrelated text member. Unsafe
ids and archive members point only into this test's controlled outside tree. Drive spellings
use the same controlled location on Windows; there is no remote share or system-file target.

Successful output must resolve within the original destination. Refusals must preserve the
outside tree. On Linux, an inotify observer also records outside modifications, deletion,
creation and moves, so cleanup cannot hide a transient write. Other platforms retain final
state and canonical-path checks; Linux observation is not claimed for them.

The structural extraction contract allows an operation to create a fresh private staging
directory in the destination's parent, then rename or remove it. The observer permits only
fresh parent directories with a complete create/remove-or-move lifecycle; writes to existing
outside objects, new outside files or links, and leaked directories still fail. Final outside
snapshots must remain unchanged. Separate operation-failure gates check staging ownership
and publication cleanup. This is the stated staging exception to the earlier universal
transient-outside-write rule, not permission for index-controlled output paths to escape.

Project-cache setup uses the documented destination layout from the collection ADR: id plus
the first twelve digest characters. The digest comes from authored bytes, not the downloader.
The same collection drives Python, the module CLI, the standalone CLI and both legacy fetch
entrances. Legacy fetch may keep an archive opaque; it must still contain all of its writes.

Existing-content cases also include staging symlinks and hard links, cached descendant
links, and an unrelated destination child. The staging suffix is a regression carrier
for the reviewed writer channel, not a required public filename. A conflicting archive
contains a regular parent file followed by its child: refusal must remain a refusal on
retry, rather than accepting an incomplete cache merely because its project marker exists.
