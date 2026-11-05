# ADR-0074: Portable bundled text

## Status

Accepted; complete native platform qualification pending.

## Context

The element table established product text embedded by CMake. Palettes, colour maps, the report
script, provider capabilities and bundled assistant skills repeated that raw-string mechanism.
A real Windows build rejects large skill strings with C2026. Repairing only a skill would leave
all earlier resource families able to hit the same compiler and delimiter limits. The engine's
own earlier compiler boundary already demonstrated the need for a shared text serializer.

## Decision

All product resource families use one CMake byte serializer. Generate constant, NUL-terminated char
arrays from explicit hexadecimal byte escapes with bounded source lines. File resources are read
as HEX directly from disk: CMake text reads normalize CRLF before a subsequent string conversion.
Only validated in-memory identity/hash metadata uses the TEXT mode. Every stored byte is
independent of source encoding, raw-string delimiters and single/concatenated string-literal limits.
Keep the original pointer-based interfaces and explicit byte lengths for string views. Storage is
immutable with static lifetime and constant initialization; no runtime joining, allocation or file
lookup is added. Manifest paths and SHA256 checks still validate original skill bytes before embedding.

The private skill-resource declarations stand alone from the assistant model/JSON implementation.
That allows an ordinary native compiler to qualify generated resources before an engine SDK or
full product build exists. Existing assistant consumers continue through their original header.

The early installer check invokes the actual production CMake generator with large UTF-8 inputs
for every resource family, compiles all generated translation units, checks bounded source tokens
and lines, and compares every exposed byte against the original input. Include quotes, backslashes,
mixed LF/CRLF/bare-CR bytes, raw-string delimiter text and multibyte characters. The Windows runner uses its real compiler; output uses binary
mode so newline conversion cannot disguise a serializer defect. Keep the observed old compiler
failure and the expected-red lexical boundary. New generated families join the same compile sweep.

## Consequences

Generated C++ source is larger, but distributed text and its byte counts remain unchanged. The
compiler emits ordinary static data rather than a giant string token. New resources must use the
shared serializer and retain independent parser/manifest validation for their format.
