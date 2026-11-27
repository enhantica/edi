# Maintenance Tool update fixtures

`installer-2026.11.27.qs` is the original `tools/installer/Installer.qs`
from release tag `v2026.11.27` (commit
`255d9fc638220a96d423e1436e3f348a7c0213ea`). Its SHA-256 is
`308d1b5dd51051da6a2720a2be6005501af55b0da96d51628fa97aeaec36086b`.
The gate supplies this script as the running tool's controller and obtains
the update component script from the current installer source. The local
adapter delivers Qt Installer Framework's operation and completion signals
and executes the resulting filesystem commands against a temporary install.

The Qt entry probe compiles the desktop app's update controller and uses its
numbered-release constructor with the installed bundle's executable path
and an empty feed list. Its launch request is the same one exposed to the
app's Maintenance Tool button. The executable under the temporary bundle
signals whether that route reached the tool.

System jobs with `pixi install -e app` use its Qt CMake prefix; other
test environments may supply the same prefix with
`EDI_MAINTENANCE_QT_PREFIX`.
