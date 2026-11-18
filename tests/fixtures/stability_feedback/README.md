# Native stability prerequisites

The existing `onboarding-probes` task calls this generator after building `log_probe`.
It compiles the complete production event-exception boundary and settings migration
functions into isolated Qt probes, then stamps their provider, fixture and binary bytes.
The gates live in `tests/integration/app` because they require the pinned Qt environment.
They refuse missing or stale prerequisites instead of building inside test timing.

`test_application_error_boundary` throws both standard and unknown exceptions through
the production application class and verifies the following event is still delivered.
A separate real RunLog probe verifies the signal consumed by the popup.
