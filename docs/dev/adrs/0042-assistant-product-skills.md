# Versioned assistant product guidance

Status: Accepted design; initial content present, runtime loading and resource browsing pending.

## Context and first prior art

The assistant already serializes revision-bound project/parameter/diagnostic and selected-file context in core/src/assistant.cpp (ADR0037); native transport consumes that same consented context (ADR0038), and ADR0041 owns disclosure/rendering. Existing core CMake capability/palette embedding is the resource prior art. Product knowledge belongs in edi, while organization/developer AGENTS and Codex skills remain exclusively in relay.

## Decision

Maintain one editable collection at data/assistant/skills/index.json and <id>/SKILL.md. The strict edi.assistant.skills/1 index carries id, version, title, summary, relative path, SHA256, declared prerequisites, actual closed tool capabilities and published references. Initial version1.0.0 resources cover project assistance, FullProf intake and GSAS intake. They guide actual inspect/read/question/approved operations; they do not provide absent conversion, project creation, runtime access or scientific success.

The next reviewed implementation embeds these exact bytes in the Qt-free core using the existing CMake resource pattern, verifies their manifest/content bond and places one selected {id,version,sha256,content} inside the same bounded current context. The existing idle select_skill command extension is explicit user authority; no implicit filename-based selection is introduced by this data commit. Disclosure, inspect_project and provider dispatch must share exact selected content and revision/hash. Current first collection is DATA ONLY: no loader/context or UI selection has landed, and no claim that the model uses it follows from these files.

Resource changes or accepted project/file/currentness changes require fresh disclosure through existing consent. Missing/changed/oversized content refuses instead of omission or truncation. UI browsing opens the same shipped content/references and truthfully distinguishes prerequisites and unsupported converter stages. No recursive include, arbitrary filesystem lookup, remote instruction fetch, all-skills dump or new tool/approval follows. File contents and constraint expressions remain untrusted data.

## Scientific provenance and limits

FullProf intake is grounded in the official manual/commands documentation and the independently recorded installed July2001 manual plus later fp2k.inf dialect notes. Legacy data arguments, COMM with NPATT, repeated banks and codeword/occupancy/profile conventions cannot be generalized from a filename/comment or one converted example. Current fullprof-intake explicitly asks for missing/ambiguous selected companions and explains that general PCR conversion is not implemented. GSAS intake asks for readable exports and never unpickles GPX. project-assistance preserves current objective/data/constraints, genuine result retention and real approval; it prescribes no universal refinement order or convergence guarantee.

Scientific converters, real FullProf/GSAS independent evaluation, fuller staged skills, browser input/runtime, Claude, live chat/follow-ups, resource loading/context metadata and complete SDK/CI/reviewer acceptance remain separate owed work. This initial content is original guidance, not copied manuals or a scientific expected-output oracle.
