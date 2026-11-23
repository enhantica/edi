# 0101. Issue labels for edi's agent flow

- **Status:** Accepted
- **Date:** 2026-11-23
- **Implementation:** 🟢 The labels below exist in `enhantica/edi` and `enhantica/edi-feedback`; the feedback service
  adds the placeholders to each issue it files
- **Priority:** Medium

## Context

edi is developed by agents. Issues arrive from the feedback service (ADR-0063) in the private `enhantica/edi-feedback`
repository; a triage agent labels them and files the public ones in `enhantica/edi`; the owner selects the work;
development tasks implement it on one branch per task, merged as a squash by the merge guard. There is no develop branch and
no outside contributor yet. Releases are planned from pull-request labels (`tools/release/plan.py`, checked by
`.github/workflows/labels.yml` and used by `release-plan.yml`).

The EasyScience projects share one label system (easyscience/.github discussion #33, extended by #49), which
easyscience/diffraction-lib carries. Its groups, colours and names are kept where edi's flow reads them. Each label
here answers one question: does the triage agent, the owner, the release plan or the task queue read it? A label
nobody reads is dropped. The set is closed: the triage agent chooses only from the labels below, by the rule given for
each.

## Decision

1. **The queue.** The feedback service gives every issue it files `[scope] ⚠️ label needed` and
   `[priority] ⚠️ label needed`; a public issue filed in `enhantica/edi` starts with them too. These two labels are the
   triage agent's queue: it replaces each with exactly one real label of the same group, or with
   `[status] needs owner decision` when the rules below do not settle it.
2. **The labels and their rules.** In `enhantica/edi` (E) and `enhantica/edi-feedback` (F):

| Label | Repos | Read by | Rule (when the triage agent sets it) |
| --- | --- | --- | --- |
| `[scope] bug` | E F | release plan (Fixed), owner | Shipped behaviour is wrong: a crash, a wrong result, a refusal of valid input, a broken control. |
| `[scope] enhancement` | E F | release plan (Added), owner | A new feature or a change of what an existing feature does. |
| `[scope] documentation` | E F | release plan (Changed) | Only documentation, tutorials or the website text change. |
| `[scope] maintenance` | E F | release plan (Changed) | Code, build, CI or tooling change with no change of behaviour a user sees. |
| `[scope] significant` | E F | release plan (Added), owner | Breaks saved projects, the Python API or the CLI, so users must act. Set only with the owner's word. |
| `[scope] ⚠️ label needed` | E F | triage queue | Set by the service or when filing; removed when a real scope is chosen. |
| `[priority] highest` | E F | owner | Data loss, a crash on start or on opening a valid project, an installer that fails, a security problem. |
| `[priority] high` | E F | owner | A main workflow fails or gives wrong results with no workaround. |
| `[priority] medium` | E F | owner | A defect with a workaround, or a requested improvement of a used feature. |
| `[priority] low` | E F | owner | An idea, a cosmetic defect or wording. |
| `[priority] lowest` | E F | owner | Kept for completeness; not set by triage (the owner may). |
| `[priority] ⚠️ label needed` | E F | triage queue | Set by the service or when filing; removed when a real priority is chosen. |
| `[status] needs owner decision` | E F | owner | Triage cannot choose the scope or priority from the rules, or the request needs a product decision (whether to do it at all). Removed when the owner decides. |
| `[maintainer] duplicate` | E F | triage agent | The same request or defect already has an issue: link it and close this one. |
| `[maintainer] invalid` | E F | triage agent, owner | Not a request or defect of edi (spam, a test message, another program's problem). |
| `[maintainer] question` | E F | triage agent | More information from the reporter is needed before it can be triaged. |
| `[maintainer] wontfix` | E F | owner | The owner decided not to do it. Never set by triage alone. |
| `[interface] desktop`, `web`, `py`, `cli`, `cli-py` | E | release plan, owner | Which interfaces the change reaches: desktop app, web app, Python package, command line, command line through Python. One or more on every pull request and public issue. |
| `[bot] release` | E | release plan | Only the release pull request; no other label is needed with it. |
| `[source] user` | E | owner | Filed from feedback whose origin is `🙋 user`. |
| `[source] maintainer` | E | owner | Filed from feedback whose origin is `🔧 owner`, or filed by the owner. |
| `[source] agent` | E | owner | Found by an agent while working on a development task. |
| `[task] <task id>` | E | task queue, owner | The issue is owned by that development task: created and set when the task is kicked off with the issue in its packet, kept after the task merges as the record of who did it. |
| `🔧 owner`, `🙋 user` | F | triage agent | The origin: the message's contact is the maintainer (or an agent's test), or anyone else. |
| `survey`, `event:<event>` | F | survey tools | Set by the service on survey answers; `tools/survey-summary.mjs` lists issues by `survey`. |
| `likes` | F | owner | Answers to the app's likes prompt (kind `likes`), when the service files them. |
| `question`, `idea`, `problem`, `feedback` | F | history only | The form's type before 2026-11-23, kept on the 47 issues that have it; never set now. |

3. **Dropped**, each carried by no issue or pull request when it went: `[maintainer] good first issue` and
   `[maintainer] help wanted` (there are no newcomers to point at; agents and the owner select work), `[bot] backmerge`
   (edi has no develop branch; the release plan no longer reads it), `[bot] release` and `[bot] backmerge` in
   edi-feedback (no pull requests there), and the `[area]` group, which nothing reads (the release plan uses
   `[interface]`; work is selected by issue).

## Consequences

- An agent can triage without judgement calls outside the rules, and the owner's queue is one label.
- An issue shows which task owns it, and a public issue shows whether a user, the maintainer or an agent raised it.

## Alternatives considered

| Alternative | Verdict |
| --- | --- |
| Copy the EasyScience set unchanged | Rejected: several labels serve human contributors or a develop branch edi does not have, and it lacks the owner's queue, the source and the owning task. |
| Keep the form's type as the only feedback label | Rejected: it says what the user chose, not impact or urgency. |
| An `[area]` group (engine, fitting, assistant, installer) | Rejected for now: nothing reads it; the interface and the task already place an issue. |
