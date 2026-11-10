# Recorded native transport

The existing independent download reference supplies collection bytes and digests.
This Linux fixture supplies libcurl's public C interface, declared by the installed
curl headers, with recorded replies only. It does not link or call real libcurl.
The data mirror remains `data.easydiffraction.org`; the separate installer mirror
is `download.easydiffraction.org`, singular.

A process-local loader shim substitutes the recorded library for any libcurl lookup,
or makes every such lookup fail. It also refuses Internet sockets, connections and
name resolution. A child preflight proves substitution and guard activation before
running any download command. No system library is hidden or changed. Missing-library
tests prove local downloads and help work, then require a clear libcurl installation
message for HTTPS. This is Linux loader evidence, not Windows or macOS qualification.

Build explicitly under the operator's shared build lock, passing a destination and
`--curl-headers` containing `curl/curl.h`. Set `EDI_TRANSPORT_FIXTURE_DIR` to that build
for the scoped gate. The source hash receipt must match; the gate never auto-builds.
