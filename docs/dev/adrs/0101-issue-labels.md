# 0101. Issue labels for edi's agent flow

- **Status:** Accepted
- **Date:** 2026-11-23
- **Implementation:** 🟢 The labels below exist in `enhantica/edi` and `enhantica/edi-feedback`; the feedback service
  adds the placeholders to each issue it files. The release plan and the label check read the names below and, for 30
  days after the labels are renamed, the names they had before (`[group] name`). `enhantica/edi-feedback` takes the
  names and colours below once the owner approves what happens to its own labels
- **Priority:** Medium

## Context

edi is developed by agents. Issues arrive from the feedback service (ADR-0063) in the private `enhantica/edi-feedback`
repository; a triage agent labels them and files the public ones in `enhantica/edi`; the owner selects the work;
development tasks implement it on one branch per task, merged as a squash by the merge guard. There is no develop branch and
no outside contributor yet. Releases are planned from pull-request labels (`tools/release/plan.py`, checked by
`.github/workflows/labels.yml` and used by `release-plan.yml`).

The EasyScience projects share one label system (easyscience/.github discussion #33, extended by #49), which
easyscience/diffraction-lib carries. Its groups, colours and words are kept where edi's flow reads them. Each label
here answers one question: does the triage agent, the owner or the release plan read it? A label
nobody reads is dropped. The set is closed: the triage agent chooses only from the labels below, by the rule given for
each.

## Decision

1. **The queue.** The feedback service gives every issue it files `⚠️ scope needed` and `⚠️ priority needed`; a public issue filed in `enhantica/edi` starts with them too. These two labels are the
   triage agent's queue: it replaces each with exactly one real label of the same group, or with
   `🤔 needs owner decision` when the rules below do not settle it.
2. **The labels and their rules.** In `enhantica/edi` (E) and `enhantica/edi-feedback` (F):

| Group | Label | Repos | Read by | Rule (when the triage agent sets it) |
| --- | --- | --- | --- | --- |
| scope | `🐞 bug` | E F | release plan (Fixed), owner | Shipped behaviour is wrong: a crash, a wrong result, a refusal of valid input, a broken control. |
| scope | `✨ enhancement` | E F | release plan (Added), owner | A new feature or a change of what an existing feature does. |
| scope | `📘 documentation` | E F | release plan (Changed) | Only documentation, tutorials or the website text change. |
| scope | `🧹 maintenance` | E F | release plan (Changed) | Code, build, CI or tooling change with no change of behaviour a user sees. |
| scope | `💥 significant` | E F | release plan (Added), owner | Breaks saved projects, the Python API or the CLI, so users must act. Set only with the owner's word. |
| scope | `⚠️ scope needed` | E F | triage queue | Set by the service or when filing; removed when a real scope is chosen. |
| priority | `🔥 highest` | E F | owner | Data loss, a crash on start or on opening a valid project, an installer that fails, a security problem. |
| priority | `🔴 high` | E F | owner | A main workflow fails or gives wrong results with no workaround. |
| priority | `🟠 medium` | E F | owner | A defect with a workaround, or a requested improvement of a used feature. |
| priority | `🟡 low` | E F | owner | An idea, a cosmetic defect or wording. |
| priority | `⚪ lowest` | E F | owner | Kept for completeness; not set by triage (the owner may). |
| priority | `⚠️ priority needed` | E F | triage queue | Set by the service or when filing; removed when a real priority is chosen. |
| status | `🤔 needs owner decision` | E F | owner | Triage cannot choose the scope or priority from the rules, or the request needs a product decision (whether to do it at all). Removed when the owner decides. |
| maintainer | `👯 duplicate` | E F | triage agent | The same request or defect already has an issue: link it and close this one. |
| maintainer | `🚫 invalid` | E F | triage agent, owner | Not a request or defect of edi (spam, a test message, another program's problem). |
| maintainer | `❓ question` | E F | triage agent | More information from the reporter is needed before it can be triaged. |
| maintainer | `🙅 wontfix` | E F | owner | The owner decided not to do it. Never set by triage alone. |
| interface | `🖥️ desktop`, `🌐 web`, `🐍 py`, `⌨️ cli`, `📦 cli-py` | E | release plan, owner | Which interfaces the change reaches: desktop app, web app, Python package, command line, command line through Python. One or more on every pull request and public issue. |
| interface | `🪟 app` | E | release plan, owner | The desktop and the web app together. The release plan reads it as those two labels. |
| interface | `🌍 all` | E | release plan, owner | Every interface. The release plan reads it as all five labels. |
| bot | `🚀 release` | E | release plan | Only the release pull request, and alone: the release plan and the label check refuse it beside another label. |
| source | `🙋 user` | E | owner | Filed from feedback whose origin is `🙋 user`. |
| source | `🔧 maintainer` | E | owner | Filed from feedback whose origin is `🔧 owner`, or filed by the owner. |
| source | `🤖 agent` | E | owner | Found by an agent while working on a development task. |
| source | `🌙 nightly` | E | owner | The one open issue "Nightly CI is red on main", kept by hand (rule 5). |
| status | `🚧 in progress` | E | owner, triage agent | A development task is working on the issue now (rule 4). |
| none | `🔧 owner`, `🙋 user` | F | triage agent | The origin: the message's contact is the maintainer (or an agent's test), or anyone else. |
| none | `survey`, `event:<event>` | F | survey tools | Set by the service on survey answers; `tools/survey-summary.mjs` lists issues by `survey`. |
| none | `likes` | F | owner | Answers to the app's likes prompt (kind `likes`), when the service files them. |
| none | `question`, `idea`, `problem`, `feedback` | F | history only | The form's type before 2026-11-23, kept on the 47 issues that have it; never set now. |

3. **Names and groups.** A label is an emoji, one space and its text, with no group name: the colour tells the group. Red
   (`#d73a4a`) is the scope, yellow (`#fbca04`) the priority, blue (`#0079b7`) the interface, light blue (`#c5def5`) the
   source, green (`#0e8a16`) the maintainer's answer, violet (`#9333EA`) the status and indigo (`#5319e7`) the bot. Every
   name is unique in its repository, so the two placeholders differ in their text. GitHub and the release plan compare
   names whole, never by a part of them: the release plan holds the list of names with their groups and colours and
   refuses a pull request with any other label. Each emoji has one exact form: `🖥️` (desktop), `⌨️` (cli) and `⚠️` (the
   placeholders) end with the variation selector U+FE0F, the others have none. `🪟 app` and `🌍 all` are short for several
   interfaces: the release plan replaces them with those, and overlapping labels are accepted and name each one once.
4. **In progress.** When a development task starts, `🚧 in progress` is set on every edi issue the task owns. When the
   task's pull request merges, each of those issues is checked against the merged code and the label is removed, whether
   the issue is done or not; it is also removed when the task stops or drops the issue.
5. **The nightly run.** There is at most one open issue for a red nightly run on `main`, "Nightly CI is red on main", with
   `🌙 nightly`, a scope and a priority. A maintainer keeps it by hand: it names the failures that are real, is updated
   instead of filing another, and is closed when a nightly run on `main` passes. Nothing files, updates or closes it
   automatically.
6. **New labels.** An agent chooses only from this list. It never creates, renames, recolours or deletes a label without
   the owner's decision, and a change of the list changes this record.
7. **Dropped**, each carried by no issue or pull request when it went: `[maintainer] good first issue` and
   `[maintainer] help wanted` (there are no newcomers to point at; agents and the owner select work), `[bot] backmerge`
   (edi has no develop branch; the release plan no longer reads it), `[bot] release` and `[bot] backmerge` in
   edi-feedback (no pull requests there), and the `[area]` group, which nothing reads (the release plan uses
   the interface; work is selected by issue). The `[task]` group, which needed a new label for every task, is dropped too:
   the in-progress label replaces it.

## Consequences

- An agent can triage without judgement calls outside the rules, and the owner's queue is one label.
- An issue shows whether it is being worked on, and a public issue shows whether a user, the maintainer, an agent or the
  nightly run raised it.

## Alternatives considered

| Alternative | Verdict |
| --- | --- |
| Copy the EasyScience set unchanged | Rejected: several labels serve human contributors or a develop branch edi does not have, and it lacks the owner's queue, the source and the work in progress. |
| Keep the group in the name (`[scope] 🐞 bug`) | Rejected by the owner: the colour says the group. |
| Keep the form's type as the only feedback label | Rejected: it says what the user chose, not impact or urgency. |
| An `[area]` group (engine, fitting, assistant, installer) | Rejected for now: nothing reads it; the interface already places an issue. |
