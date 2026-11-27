# 0108. Assistant providers and accounts

- **Status:** Proposed
- **Date:** 2026-11-27
- **Implementation:** ⬜ Not implemented
- **Priority:** High
- **Forward constraint (binding on new features):** an assistant runtime is reached only through an
  `AssistantProvider`, and a runtime other than Codex reaches edi's tools only through edi's tool server; nothing
  outside a provider names a runtime's methods or fields. edi chooses each account's config home but never reads,
  copies, stores or passes the credentials inside it.

This ADR extends ADR-0055 (the provider transport behind the controller), ADR-0056 (provider connections), ADR-0057
(the panel, the Codex runtime and its account card), ADR-0058 (product skills), ADR-0071 (installers) and ADR-0091
(code signing). It keeps every rule they set except the clauses named under "What this replaces".

## Context

The desktop assistant speaks one runtime, OpenAI's Codex app-server, so only ChatGPT users can use it. The owner
asked (2026-11-27, edi #116) for Claude and GitHub Copilot beside ChatGPT: several accounts per provider, shown and
switched from the account button, and one installer checkbox per assistant. An organisation that allows only Copilot
can then use the assistant with its own data.

What exists:

- `AssistantViewModel` (`app/src/assistant_view_model.cpp`) reaches Codex through `CodexAgent`
  (`app/src/codex_agent.*`) and its `generic_*` functions: initialize, sign-in, thread start and resume, turns, events,
  items, server requests, native replies. Production always takes this path. Codex method names and fields are spread
  across the view model.
- ADR-0056's direct ChatGPT connection (`assistant/native/chatgpt_connection.*`: sign in, connect saved, send, cancel,
  sign out, state) is the second path. The `NativeDependencies` constructors of `AssistantViewModel` and `Session`
  select it; it is the diagnostic door of ADR-0057 and the path the native tests inject. It handles its own OpenAI
  tokens under ADR-0056's rules. The view model switches between the two paths at each use (`generic_mode ? … :
  connection->…`).
- The tool catalogue (`assistant_native_tool_specs`), the dispatcher (`native_dispatch`), the guard
  (`app/tools/assistant_guard.cpp`), history and work reports do not depend on Codex underneath. Only the edges do:
  the call is checked against a Codex `dynamicToolCall` item, and the reply is wrapped as Codex `contentItems`.
- ADR-0058 stages the bundled skills into `.agents/skills` in edi's prepared workspace and confirms them with Codex's
  `skills/list`. That is Codex's discovery, not a neutral one.
- ADR-0056 already set the rule for Claude: "native Claude uses its own supported sign-in/runtime, not extracted
  subscription tokens".
- ADR-0057 forbids assigning `HOME` or `CODEX_HOME`, so one Codex login is all edi can use.
- ADR-0071 ships Codex as one optional installer component under `libexec/edi/codex` and offers it as one checkbox.
  ADR-0091 signs the runtime's helper programs with edi's identity.
- ADR-0023 §6 keeps the assistant off the web app.

The owner fixed the shape (2026-11-27): Claude through the bundled, unmodified Claude Code binary and the user's own
Claude subscription signed in through that binary, with no API-key entry in edi; Copilot through the bundled,
unmodified Copilot CLI and its own sign-in, for personal and business seats and GHE.com hosts; several accounts per
provider; three installer checkboxes; desktop only.

## Decision

### 1. One provider interface, with ChatGPT's two paths behind it

ADR-0055's seam stays the only seam: the host supplies a provider transport and the controller and view model see
normalized events. `AssistantProvider` (`app/src/assistant_provider.hpp`) is that transport's interface. It is an
abstract `QObject` that owns one runtime (or connection) for one account and turns its protocol into edi's terms. The
view model holds one active provider and never sees a runtime method name or field.

```cpp
enum class AssistantProviderId : unsigned char { ChatGpt, Claude, Copilot };  // settings keys chatgpt|claude|copilot
struct AssistantAccountRef { AssistantProviderId provider; QString id, home, host; };
struct AssistantThreadRequest { QString thread, workspace, instructions, model, effort; QJsonArray tools; };
struct AssistantTurnRequest  { QString thread, steerTurn, clientMessageId, model, effort; QJsonArray input; };
struct AssistantToolCall     { QJsonValue token; QString callId, tool, thread, turn; QJsonObject arguments; };

class AssistantProvider : public QObject {
    Q_OBJECT
public:
    virtual AssistantProviderId id() const = 0;
    virtual QString executable() const = 0;            // empty when the runtime is not installed
    virtual bool start(const AssistantAccountRef&, const QString& workspace) = 0;
    virtual void retire() = 0;                         // stop; late output is dropped
    virtual quint64 generation() const = 0;            // the fence every queued reply checks
    virtual void readAccount() = 0;                    // identity readback, before any input
    virtual void signIn() = 0;                         // the runtime's own browser or device flow
    virtual void cancelSignIn() = 0;
    virtual void signOut() = 0;
    virtual void listModels() = 0;
    virtual void selectModel(const QString& thread, const QString& model, const QString& effort) = 0;
    virtual bool reportsUsage() const = 0;
    virtual void refreshUsage() = 0;
    virtual void prepareSkills(const QString& workspace) = 0;  // stage and verify the approved skills
    virtual void openThread(const AssistantThreadRequest&) = 0;  // start, or resume when thread is set
    virtual void sendTurn(const AssistantTurnRequest&) = 0;      // start, steer or queue
    virtual void cancelTurn(const QString& thread, const QString& turn) = 0;
    virtual void answerTool(const AssistantToolCall&, bool success, const QByteArray& result) = 0;
    virtual void answerQuestion(const QJsonValue& token, const QJsonObject& answers) = 0;
signals:
    void started();
    void failed(int kind, const QString& explanation);
    void accountRead(const QJsonObject& identity);     // {email, plan, host}
    void accountRefused(const QString& reason);        // no seat, organisation policy, signed out
    void signedOut();
    void signInOpened(const QUrl& url, const QString& code);
    void toolsVerified(const QStringList& tools);      // the effective tool set, read back
    void skillsVerified(const QStringList& skills);
    void modelsListed(const QJsonArray& catalogue);
    void usageChanged(const QJsonObject& snapshot);
    void threadOpened(const QString& thread, const QJsonObject& settings);
    void turnStarted(const QString& thread, const QString& turn);
    void item(const QString& thread, const QString& turn, const QJsonObject& item, bool completed);
    void textDelta(const QString& thread, const QString& turn, const QString& item, const QString& delta);
    void turnFinished(const QString& thread, const QString& turn, const QString& status, const QJsonObject& error);
    void toolCall(const AssistantToolCall&);
    void question(const QJsonValue& token, const QJsonArray& questions);
    void questionResolved(const QJsonValue& token);
};
```

The thread browser calls (list, rename, archive, read items) and the deadline controls of `CodexAgent`
(`beginOperation`, `beginHumanWait`, `beginNativeWork` and their ends) move onto the interface unchanged; a provider
that has no thread browser reports that, as ADR-0057's states already allow. Signals use direct connections, so every
handler runs in today's order. The value shapes are the ones the view model already uses: the model catalogue row,
the usage snapshot, the prepared question.

**ChatGPT through Codex, first, with no behaviour change.** `CodexProvider` (`app/src/codex_provider.*`) owns an
unchanged `CodexAgent`; `CodexAgent` keeps its name, header and public API. Every Codex payload and parser moves out
of the view model into `CodexProvider`: `initialize`, `account/read`, `account/login/start` and its URL check,
`skills/list`, `thread/start|read|resume`, `thread/settings/update` and the policy proofs, `turn/start|steer`, the
event and item parsing and `codexErrorInfo` mapping, `item/tool/call` with the `dynamicToolCall` snapshot check, the
`{success, contentItems}` reply wrapper, `requestUserInput`, `turn/interrupt`, `account/rateLimits/*`, `model/list`,
and the `thread/list|name/set|archive|items/list` browser. What stays in the view model is edi's: consent and
disclosure, workspace preparation, instruction text, rows, timers, queue, receipts, the work report, the question
card, dispatch and admission. The dispatcher splits at the snapshot check: the rest of `native_dispatch` becomes
`native_admit(const AssistantToolCall&)`, which every provider's calls enter.

**ChatGPT through the direct connection, second.** `NativeChatGptProvider` (`app/src/native_chatgpt_provider.*`) owns
the `ChatGptConnection` the `NativeDependencies` constructors build, and does what the view model's
`connection->…` branches do today, in the same order: `signIn` is `sign_in()`, `sendTurn` is the controller's prepared
`send()`, `cancelTurn` is `cancel()`, `signOut` is `sign_out()`, the state readback is `state()`. Its credential
handling stays exactly ADR-0056's; this ADR does not touch it. Thread browser, usage and skills report "not offered",
as that path does today. The view model's `generic_mode` switches become calls on the active provider, so neither
ChatGPT path is outside the adapter.

**Activity rows keep their shape.** Saved history rows store item payloads whose types began as Codex's
(`agentMessage`, `reasoning`, `dynamicToolCall`, `plan`, …). That shape becomes edi's activity item schema. Claude
and Copilot map their events into it, so presentation code and saved history files stay as they are.

### 2. One process transport

The neutral half of `CodexAgent` becomes `AssistantProcess` (`app/src/assistant_process.*`): start through the guard
(`guard <appPid> <runtime> <args…>`), newline framing with the JSON size limits, operation deadlines and their
suspension, generation fencing and `retire()`, stderr drained and never shown, and the exit-code mapping (127, 125,
128+n). `CodexAgent` keeps its API on top of it. The JSON size helpers move to `app/src/assistant_json_size.hpp`
under neutral names, with the `codex_*` names kept as aliases.

Each provider builds its child's environment from the app's environment: it sets the account's config home and the
settings in sections 4 and 5, and removes the variables listed there. The guard does not touch the environment, so
what the provider builds is what the runtime gets.

### 3. edi's tools as an MCP server

Claude and Copilot call edi's tools over the Model Context Protocol, revision 2025-11-25, stdio transport. The runtime
starts the server as its own child, so the server is a small bridge to the app:

- **A mode of the existing guard.** `edi_assistant_guard mcp` copies newline-delimited messages between its stdin and
  stdout and an app-owned local socket. It checks for `mcp` before `setsid()`, so it stays in the runtime's process
  group (Unix) or job (Windows) and dies with it; it exits when either side closes. It holds no tool knowledge. No new
  executable is installed, signed or hashed.
- **App side.** `AssistantToolServer` (`app/src/assistant_tool_server.*`) listens on a `QLocalServer` with a random
  name, owner-only. The name and a random key reach the bridge through the server entry's environment
  (`EDI_ASSISTANT_TOOLS`, `EDI_ASSISTANT_TOOLS_KEY`) in a config file that lives in edi's prepared workspace with
  owner-only permissions, never through arguments, which other users can read in the process list. The bridge's first
  line is the key; the server accepts one connection per runtime process and binds it to that process's generation.
- **Lifecycle.** The server answers `initialize` with the client's `protocolVersion` when edi supports it (2025-03-26
  to 2025-11-25), otherwise 2025-11-25, and `capabilities: {tools: {listChanged: false}}`; it answers `ping`.
- **`tools/list`** returns the catalogue the view model builds for the thread (`AssistantThreadRequest::tools`, today's
  `dynamicTools`) as `name`, `description` and `inputSchema`, plus `request_user_input` (below). MCP requires a root
  `type: "object"`, so the union schemas (`set_experiment_type`, `edit_structure`, `edit_atom`, `edit_relation`) are
  flattened in this projection only: the union of their properties, `required` limited to what every branch requires,
  the selector as one enum. The exact branch check stays in `assistant_native_arguments`, which every call already
  passes. Each tool carries `_meta: {"anthropic/alwaysLoad": true, "anthropic/maxResultSizeChars": 500000}`, so
  Claude loads it up front and never moves a result to a file the model cannot read. ChatGPT's `dynamicTools` do not
  change.
- **`tools/call`** becomes an `AssistantToolCall` for the active turn of the process it came through and enters the
  same `native_admit` as ChatGPT's calls. A call with no running turn, after Stop, from a retired process, or before
  the tool set was verified (sections 4, 5) is refused. The reply is the same projected JSON ChatGPT receives, as
  `{content: [{type: "text", text: <outgoing JSON>}], isError: !success}`. `notifications/cancelled` cancels the native
  call through the path Codex's `serverRequest/resolved` uses.
- **Questions.** `request_user_input` is edi's question tool for Claude and Copilot, with the schema of Codex's tool of
  the same name (at most three questions, options to click, a free answer). A call becomes the pending question card
  Codex's questions use today, and its answer is the tool result. edi's instructions already name the tool, so the
  same text serves every provider. The runtimes' own question tools stay off (sections 4, 5).
- **Names.** The server is called `edi`; the models see `mcp__edi__<tool>` (Claude) and `edi-<tool>` (Copilot).
- **Timeouts.** A fit or a question can outlast a runtime's default MCP call timeout, so each runtime's config gives
  edi's server edi's longest native deadline (section 4: `MCP_TOOL_TIMEOUT`; section 5: the entry's `timeout`).

The guard, the catalogue and the dispatcher stay one implementation for all three providers.

### 4. Claude

One long-lived process per open thread, started through the guard in edi's prepared workspace:

```
claude -p --input-format stream-json --output-format stream-json --verbose --include-partial-messages
  --mcp-config <workspace>/.edi/claude-mcp.json --strict-mcp-config
  --tools "Skill" --allowedTools "mcp__edi__*,Skill"
  --setting-sources local --plugin-dir <workspace>/.edi/claude-plugin
  --model <id> [--effort <level>] (--session-id <new uuid> | --resume <uuid>)
  --append-system-prompt-file <workspace>/.edi/instructions.md
```

- **Tools.** `--tools "Skill"` leaves one built-in tool, the skill loader the bundled skills need; command, file,
  web, agent and question tools are off. `--tools` does not govern MCP tools, so `--strict-mcp-config` with one config
  holding only edi's server is what limits them. `--allowedTools` pre-allows edi's tools and the loader; any other
  permission request is denied, since `-p` has nobody to ask and no permission prompt tool is named.
- **Settings.** No user or project settings load: `--setting-sources local` reads only
  `<workspace>/.claude/settings.local.json`, which edi's prepared workspace never contains (a present one refuses
  the start). So no hooks, MCP servers, `CLAUDE.md` or API-key helpers from elsewhere apply.
- **Environment.** `CLAUDE_CONFIG_DIR=<account home>`, `DISABLE_UPDATES=1`, `MCP_TOOL_TIMEOUT=<longest native
  deadline in ms>`. The child gets none of the inherited Anthropic credential and routing variables:
  `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_PROFILE`,
  `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `CLAUDE_CODE_USE_FOUNDRY` and `CLAUDECODE` are removed. A turn
  therefore runs as the account signed in through the binary's own login in that home, and nothing else.
- **Sign-in and sign-out** run the binary's own `claude auth login` and `claude auth logout` with the account's
  `CLAUDE_CONFIG_DIR`, with no flag that picks or removes a method: the binary's login screen keeps every method it
  has, and edi sets no `forceLoginMethod` or other setting that restricts one. edi shows the URL the binary prints,
  with an Open button, and a field for the code when the binary asks for one. edi offers no API-key entry of its own.
- **Identity readback, before any input.** `claude auth status` in the account's home (JSON output) must report a
  signed-in `authMethod`; then the `initialize` control reply's `account` gives the e-mail and plan, which must match
  the account's record. A mismatch or a signed-out home stops before any input, with the reason shown. edi never
  opens a file inside the home.
- **Tool and skill readback, before any input.** The `initialize` reply's `commands` must list each bundled skill
  (as `edi:<id>`); the runtime must have listed edi's tools through edi's server; and the `system/init` message's
  `tools` must hold only `Skill` and `mcp__edi__*` names, with `edi` the only MCP server. The documented stream sends
  `system/init` first, so edi waits for it before the first user message. If a pinned release sends it only after a
  first message, edi checks it before accepting any reply or running any tool call, and the pin's sign-in trial
  records which behaviour it has.
- **Skills.** The same approved skill bytes as ADR-0058's `.agents/skills` are staged as a plugin,
  `<workspace>/.edi/claude-plugin/.claude-plugin/plugin.json` naming `edi` plus `skills/<id>/SKILL.md`. Plugin skills
  load from `--plugin-dir` independently of setting sources.
- **Turns.** `initialize` first; a turn is one `user` message whose `uuid` is edi's client message id. A message sent
  during a turn is a steer. Stop sends the `interrupt` control request. The turn ends at `result`; edi checks
  `is_error` and the assistant message's `error`, not only `subtype`, because a signed-out turn reports `success`
  with `is_error: true`.
- **Models** come from the `initialize` reply (`value`, `displayName`, `supportedEffortLevels`). A model change during
  a thread uses `set_model`; an effort change restarts the idle process with `--resume` before the next turn. No
  advertised default effort means the provider default (ADR-0057).
- **Usage** comes from `rate_limit_event`: `five_hour` is the session limit and `seven_day` the weekly limit, the
  windows ChatGPT already shows. Values are the last ones seen and marked stale between turns.
- **Threads.** edi chooses the session id. A resumed thread starts a new process with `--resume`; its earlier rows come
  from edi's own history file.
- **Version.** One pinned release. Every pin change repeats the owner's sign-in trial.

Product text says "Claude"; "Claude Code" appears only in notices and in docs that say what edi runs.

### 5. GitHub Copilot

One process per active account, one ACP session per thread:

```
copilot --acp --stdio --no-auto-update --disable-builtin-mcps
  --excluded-tools <every built-in tool> --allow-tool edi
  --additional-mcp-config @<workspace>/.edi/copilot-mcp.json
```

- **Tools.** Every built-in tool, shell, file, web fetch and its own question tool included, is excluded; edi's
  server is the only MCP server and its tools are pre-allowed. edi never sets `--allow-all`, `--yolo`,
  `COPILOT_ALLOW_ALL` or the autopilot mode.
- **Environment.** `COPILOT_HOME=<account home>`, `COPILOT_AUTO_UPDATE=false`,
  `COPILOT_SKILLS_DIRS=<workspace>/.agents/skills`, and `GH_CONFIG_DIR` pointing at an empty edi-owned folder so the
  CLI finds no `gh` login. Removed: `COPILOT_GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN`, `GH_HOST`, `COPILOT_GH_HOST`,
  `COPILOT_ALLOW_ALL`, `COPILOT_MODEL`, `COPILOT_PROVIDER_*` and `COPILOT_PROVIDERS_CONFIG`.
- **edi's tools** come through `--additional-mcp-config`, whose entry sets `timeout` to edi's longest native deadline;
  ACP's `session/new` server entry has no timeout.
- **Protocol.** JSON-RPC 2.0 over stdio. `initialize` with `protocolVersion: 1` and client capabilities naming no
  `fs` and no `terminal`; `session/new` with the workspace as `cwd`; then `session/set_config_option` for the model,
  and for the effort when one is chosen. `session/prompt` runs a turn and `session/update` streams it; a message sent
  during a turn waits in edi's queue. Stop sends `session/cancel` and answers every open permission request
  `cancelled`. Resume uses `session/load`; its replayed updates are not shown again, because edi's history file
  holds the rows. A thread is recorded once its first turn ends, since the CLI saves no session without a turn.
- **Permissions.** Every `session/request_permission` is answered `reject_once`, never with a JSON-RPC error. Every
  `elicitation/create` is declined; questions come through `request_user_input`.
- **Tool and skill readback, before any input.** ACP lists neither tools nor skills directly, so edi reads back what
  it can: the runtime must have listed edi's tools through edi's server, and the `available_commands_update` must
  list each bundled skill. During a turn, a `tool_call` update for any tool that is not one of edi's cancels the turn
  and retires the process with an error, so a built-in tool cannot act unnoticed.
- **Instructions.** edi writes its instructions to `AGENTS.md` in the workspace, the CLI's custom instructions file.
- **Sign-in** runs `copilot login [--host https://<name>.ghe.com]` with the account's `COPILOT_HOME` and the empty
  `GH_CONFIG_DIR`. edi shows the lines the CLI prints (the URL and the device code) with an Open button; exit code 0
  is success. If the CLI asks to keep the token in a plain file because no system keychain exists, edi shows the
  question with Yes and No, No by default.
- **Identity readback, before any input.** The login lives in the OS keychain, not in `COPILOT_HOME`, so edi reads
  the signed-in user and host from the runtime and compares them with the account's record before the first prompt;
  a mismatch stops with the reason shown.
- **No seat, organisation policy, signed out.** `-32000` on `session/new` means signed out. Any other refusal shows
  the CLI's message as it is, plus any `notice` update. A server whose `tools/list` never arrives shows that the
  organisation's policy may block edi's tools.
- **Sign-out.** The CLI has no non-interactive logout. edi stops the process, deletes the home folder it created and
  marks the account signed out; the dialog says the GitHub sign-in stays in the system keychain until it is removed or
  revoked on GitHub.
- **Usage** is not reported (`Unsupported`, an existing state).
- **Version.** One pinned release. Copilot on Linux needs the system's OpenSSL 3.

### 6. What a runtime may do

The same rule for all three: the runtime's own tools that read or write files, run commands, fetch the web or start
agents are off; edi's tools, edi's question tool and the skill loader are on (ChatGPT's hosted `web_search` stays as
ADR-0057 has it); every other permission request is declined; no runtime updates itself; the working folder is edi's
prepared workspace. A runtime writes only inside its config home, its cache and the OS credential store.

### 7. Skills per provider

The approved skill bytes of ADR-0058 are staged once into `<workspace>/.agents/skills` and verified against their
manifest. Each provider's `prepareSkills` puts those same bytes where its runtime reads them and verifies discovery:
Codex reads `.agents/skills` and confirms with `skills/list` (unchanged); Claude reads the plugin copy (section 4) and
lists the skills in `commands`; Copilot reads `.agents/skills` through `COPILOT_SKILLS_DIRS` and lists them in
`available_commands_update`. A skill missing from any discovery stops the start, as a failed `skills/list` does today.

### 8. Accounts and config homes

edi keeps the account list; a runtime only says who is signed in.

- **Record.** `{id, provider, home, email, plan, host}`; `id` is a UUID edi creates, never derived from the e-mail.
  `AssistantAccount` gains `id` and `provider`; the view model exposes `accounts` and `activeAccount`. No record holds
  a token, a path to a token or anything read from a home.
- **Storage**, in the existing settings file (ADR-0031): `Assistant/Providers/<provider>/accounts` as
  `{version: 1, accounts: [...]}`, `Assistant/activeAccount` as `<provider>/<id>`, and the per-provider thread records
  and selection. A ChatGPT thread record with no `account` belongs to the first ChatGPT account, so today's records
  keep their shape.
- **Homes.** Each account except the first ChatGPT one gets `<AppLocalData>/assistant/accounts/<provider>/<id>`,
  created empty by edi, owner-only on POSIX, and given to the runtime as `CODEX_HOME`, `CLAUDE_CONFIG_DIR` or
  `COPILOT_HOME`. edi never opens anything inside it, and never adopts `~/.claude` or `~/.copilot`.
- **The existing ChatGPT login.** The first ChatGPT account has `home: ""`: `CODEX_HOME` stays unset and the runtime
  starts with today's environment, so nobody signs in again. Its record is written the first time `account/read` in the
  default home returns a ChatGPT account.
- **Threads.** Each record names its provider and account. The thread browser lists the active account's threads:
  ChatGPT's from the runtime as today, Claude's and Copilot's from edi's records. Opening a thread of another account
  says "This conversation belongs to <account> (<provider>)" with Switch account and Cancel, in place of today's refusal
  of a different e-mail. A home that reports another identity than its record is an error; edi never relabels the
  record.
- **Switching** retires the current process as sign-out does, without logging out, advances the usage epoch every
  queued reply already checks, starts the other account's runtime and opens an empty conversation. It is refused while
  a turn or trial runs, with Clear's rule and wording.
- **Private roots.** The file tools refuse `~/.claude`, `~/.copilot`, `$CLAUDE_CONFIG_DIR`, `$COPILOT_HOME` and
  `<AppLocalData>/assistant/accounts` beside today's roots.

### 9. The Account dialog

The account button (`connectionButton`) keeps its place, size and states, and keeps opening the Account dialog
(`accountDialog`, ADR-0057's account card); it stays the one account surface. The dialog gains one group per provider:
a header with the provider's name, one row per account with the active one checked and its e-mail, plan and state, a
Switch action on the others, Sign out on each signed-in account, and "Add account" per installed provider (disabled,
with a tooltip naming the Maintenance Tool, when the runtime is not installed). E-mail, plan and usage show for the
active account where the provider has them. Every element copies the closest existing one in the panel and its
dialogs. The consent dialog before the first sign-in (`AssistantConnectionDialog.qml`) names the provider and the
company that receives the data (OpenAI, Anthropic, GitHub); Copilot's adds a host field, `github.com` by default.
Account states: not installed, signed out, signing in, signed in, needs attention, no seat.

### 10. Packaging

Each runtime is a pinned conda package built from the vendor's download with a SHA-256 per platform, like
`edi-assistant-runtime` (`tools/deps/assistant-runtime/`):

| | ChatGPT | Claude | GitHub Copilot |
|---|---|---|---|
| package | `edi-assistant-runtime` | `edi-claude-runtime` | `edi-copilot-runtime` |
| source | Codex app-server release | Claude Code release from `downloads.claude.ai`, hash from its signed manifest | npm `@github/copilot-<platform>` package |
| installed at | `libexec/edi/codex` | `libexec/edi/claude` | `libexec/edi/copilot` |
| developer override | `EDI_CODEX_DEVELOPMENT_EXECUTABLE` | `EDI_CLAUDE_DEVELOPMENT_EXECUTABLE` | `EDI_COPILOT_DEVELOPMENT_EXECUTABLE` |

The CMake checks of ADR-0071 become one function used per runtime; the Codex-only checks stay with Codex. The bytes
are never relocated, patched or stripped. The assistant is available when any runtime is installed; each provider
reports its own, and the app offers Add account only for installed ones.

### 11. Installer components

"Also install the AI assistant" becomes three checkboxes, ChatGPT, Claude and GitHub Copilot, each its own optional
component with its size, depending on the app. ChatGPT keeps `org.easydiffraction.app.assistant`, so no `Replaces`
step is needed; the new ones are its siblings `org.easydiffraction.app.claude` and `org.easydiffraction.app.copilot`.
ChatGPT is ticked and the two new ones are not. The Maintenance Tool page lists all three and adds or removes each
without touching the others. On macOS every runtime stays outside the signed `.app`. Offline installers bundle every
component, as ADR-0071 says. Until enhantica has accepted Anthropic's Commercial Terms, the Claude component is built
but not offered.

### 12. Signing

Codex keeps ADR-0091's practice. The `claude` and `copilot` binaries are shipped unmodified, and a new signature
changes the file, so they are never re-signed: `release_executables` (`tools/installer/build.py`) leaves
`libexec/edi/claude` and `libexec/edi/copilot` out, on macOS and in the Windows `*.exe` sweep. Packaging checks each
binary's SHA-256 against its pin and its vendor signature (`codesign --verify --strict` with the expected authority,
`signtool verify /pa`) after staging and again after edi's own signing.

### 13. Notices and terms

Each runtime ships its licence text as published. Claude Code's notice names the terms that apply by plan:
Anthropic's Commercial Terms for Team, Enterprise and API users, the Consumer Terms for Free, Pro, Max and Ultra
users. The Copilot CLI ships its `LICENSE.md` and the other licence files of the package edi redistributes.
`DEPENDENCIES.md` and `THIRD-PARTY-NOTICES` gain a section each. The web app's desktop-only message names the three
providers.

### 14. What this replaces

- ADR-0057, "Generic official-runtime native prototype": "Edi never reads/copies auth/config or assigns HOME/CODEX_HOME"
  becomes "Edi never reads or copies auth/config and never assigns HOME; it assigns CODEX_HOME only to an empty
  account home it created (ADR-0108 §8)".
- ADR-0057, "Bundled official runtime": "no profile, HOME/CODEX_HOME or credential-store redirection occurs" becomes
  "no profile or HOME redirection occurs; CODEX_HOME is set only for an added account (ADR-0108 §8), and the
  credential store is the runtime's own".
- The comment in `app/src/codex_agent.cpp` that says never to assign `CODEX_HOME` changes in the same commit as the
  code that assigns it.
- ADR-0071, "Optional assistant component": the single checkbox becomes three components (§11).
- ADR-0091, "What is signed": the runtime helpers it signs are Codex's; the Claude and Copilot binaries are not signed
  (§12).

### 15. Out of scope

The web app (ADR-0023 §6); an API-key entry of edi's own; GitHub Enterprise Server, which the Copilot CLI reaches only
with a token in the environment; voice input; new tools; Copilot's bring-your-own-key providers.

## Consequences

- A fourth runtime is one more `AssistantProvider`, package and component; the tools, dispatcher and history stay.
- Codex code leaves the view model, which shrinks it, and both ChatGPT paths behave as before.
- Users of a Copilot-only organisation can use the assistant with their seat.
- The offline installer grows by about 300 MB per platform, and the installed Claude and Copilot runtimes take a few
  hundred MB each.
- Both new runtimes release often; each pin bump repeats the sign-in trial. Copilot's ACP mode is a public preview.
- Copilot keeps every account's token under one keychain service; signing out in edi leaves it there.
- Claude and Copilot threads list only conversations started in edi.
- A fresh ChatGPT account home does not inherit the user's own Codex extensions.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Write each new provider in the shape of `ChatGptConnection` | Rejected: it handles provider tokens itself. |
| Leave `ChatGptConnection` outside the adapter | Rejected: two ways to reach a provider; the view model's per-call switches would stay. |
| Claude's control-channel permission prompts and `AskUserQuestion` | Rejected: the stdio permission channel is not a documented CLI option; edi's own question tool serves all three. |
| Claude's in-process SDK MCP server | Rejected: documented only through the Agent SDK; Copilot has no equivalent, so two tool paths. |
| An HTTP MCP server inside the app | Rejected: a listening port, and a URL that changes every run. |
| A new helper executable for the tool bridge | Rejected: one more program to install, sign and check, for a bridge the guard carries. |
| Claude skills in `.claude/skills` with project settings on | Rejected: project settings would also load hooks and other configuration. |
| Copy `~/.codex` into the first account's home | Rejected: edi never reads or copies auth files. |
| Download the runtimes at install time | Rejected: offline installs and pinned hashes need the bytes. |
| Re-sign the vendor binaries with edi's identity | Rejected: both are shipped unmodified. |

## Sources

- MCP 2025-11-25: <https://modelcontextprotocol.io/specification/2025-11-25/server/tools>,
  <https://modelcontextprotocol.io/specification/2025-11-25/basic/transports>.
- Claude Code: <https://code.claude.com/docs/en/cli-reference>, <https://code.claude.com/docs/en/headless>,
  <https://code.claude.com/docs/en/env-vars>, <https://code.claude.com/docs/en/skills>,
  <https://code.claude.com/docs/en/tools-reference>, <https://code.claude.com/docs/en/mcp>,
  <https://code.claude.com/docs/en/agent-sdk/typescript>, <https://code.claude.com/docs/en/legal-and-compliance>.
- GitHub Copilot CLI: <https://docs.github.com/en/copilot/reference/copilot-cli-reference/acp-server>,
  <https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference>,
  <https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-skills>,
  <https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference>.
- ACP: <https://agentclientprotocol.com/protocol/v1/session-setup>, `/prompt-turn`, `/session-config-options`.
- Qt Installer Framework: <https://doc.qt.io/qtinstallerframework/ifw-component-description.html>.
