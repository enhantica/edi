# ADR-0073: Portable UTC timestamps

## Status

Accepted; Windows qualification pending.

## Context

The report model already selected the Windows UTC routine, but project timestamps and report saving
still used POSIX-only calls. These paths must preserve their existing STAR, ISO and display formats
when the C++ application builds on Windows. The existing report-model conversion is the prior art.

## Decision

Use one private UTC conversion helper for project metadata, report-model creation and saved report
timestamps. POSIX uses gmtime_r/timegm; Windows uses gmtime_s/_mkgmtime with the documented argument
order. Refuse a failed calendar conversion instead of formatting uninitialized fields. An unsupported
parsed Windows date has no epoch value; existing invalid-stamp fallbacks remain in place. Keep every
successful persisted timestamp format and the project's strictly advancing save policy unchanged.

A native compiler fixture exercises the actual helper with known UTC epochs, a leap-day boundary,
a date beyond the 32-bit rollover, all existing output spellings, different process timezones and
an out-of-range calendar value. Run this offline before the full native installer build.

## Sources

- [Microsoft gmtime_s](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/gmtime-s-gmtime32-s-gmtime64-s)
- [Microsoft _mkgmtime](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/mkgmtime-mkgmtime32-mkgmtime64)
