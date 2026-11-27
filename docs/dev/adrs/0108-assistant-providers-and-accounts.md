# 0108. Assistant providers and accounts

- **Status:** Proposed
- **Date:** 2026-11-27
- **Implementation:** ⬜ Not implemented
- **Priority:** High
- **Forward constraint (binding on new features):** an assistant runtime is reached only through an
  `AssistantProvider`, which maps it onto edi's assistant protocol; every runtime reaches edi's tools only through edi's
  one catalogue, guard and dispatcher, by Codex's `dynamicTools` for ChatGPT and by edi's MCP tool server for the others. edi chooses each account's config home but never reads, copies, stores or passes the
  credentials inside it.

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
normalized events. `AssistantProvider` (`app/src/assistant_provider.hpp`) is that transport's interface: an abstract
`QObject` that owns one runtime (or connection) for one account. The view model holds exactly one active provider,
built by a factory from the active account, and reaches the runtime only through it.

**edi's assistant protocol.** The view model already speaks one message vocabulary: the app-server JSON-RPC methods,
events, server requests and item shapes it uses with Codex (`initialize`, `account/*`, `model/list`, `skills/list`,
`thread/*`, `turn/*`, `item/*`, `item/tool/call`, `item/tool/requestUserInput`, `account/rateLimits/*`). That
vocabulary becomes edi's assistant protocol, the way the saved activity rows already keep Codex's item shapes. A
runtime provider takes requests and notifications in it and emits responses, events and server requests in it:

```cpp
enum class AssistantProviderId : unsigned char { ChatGpt, Claude, Copilot };  // settings keys chatgpt|claude|copilot
struct AssistantAccountRef { AssistantProviderId provider; QString id, home, host; };

class AssistantProvider : public QObject {
    Q_OBJECT
public:
    virtual AssistantProviderId id() const = 0;
    virtual bool start(const QString& workspace) = 0;        // the account was given at construction
    virtual void retire() = 0;
    virtual quint64 outputGeneration() const = 0;            // the fence every queued reply checks
    // edi's assistant protocol: CodexAgent's existing public API, unchanged.
    virtual QString request(const QString& method, const QJsonObject& params, const std::function<bool(const QString&)>& prepare = {}) = 0;
    virtual bool notification(const QString& method, const QJsonObject& params = {}) = 0;
    virtual bool answer(const QJsonValue& originalId, const QJsonObject& result, …) = 0;
    virtual bool reject(const QJsonValue& originalId) = 0;
    // … resolved, deferServerRequest, resumeDeferredRequests, activity, the deadline controls
    // (beginOperation, beginHumanWait, beginNativeWork and their ends), failure state.
    virtual QJsonObject threadPolicy() const = 0;            // the readback a thread must show (below)
signals:
    void started();
    void response(const QString& id, const QString& method, const QJsonObject& envelope);
    void serverRequest(const QJsonValue& originalId, const QString& method, const QJsonObject& params);
    void event(const QString& method, const QJsonObject& params);
    void failed(const QString& explanation);
    // … the optional usage signals CodexAgent has.
};
```

The declared methods are `CodexAgent`'s public API as it stands, so the view model's calls and connections do not
change shape, and ADR-0057's synchronous hooks stay where they are: a request's before-write `prepare` callback, a
tool reply's preparation and handoff with its `delivered` result, a question answer's `admit` predicate, the
account-confirmation deferral, owner state, failure kind and `reject`/`resolved`. A translating provider calls each
hook at the same point before its own write that `CodexAgent` does. Signals use direct connections, so every handler
runs in today's order.

**ChatGPT through Codex, first, with no behaviour change.** `CodexProvider` is `CodexAgent` itself, now deriving
from `AssistantProvider`: same name, header, API and behaviour. The one Codex-only part the view model checks, the
thread policy readback (read-only sandbox, approval policy `never`, reviewer `user`, model provider `openai`, the
`ediPolicy` proof), is what `CodexAgent::threadPolicy()` returns; the view model compares a thread's readback with the
active provider's `threadPolicy()` in place of literals. The same fields keep the same values, so ChatGPT's checks do
not change.

**Claude and Copilot translate.** `ClaudeProvider` and `CopilotProvider` map edi's assistant protocol onto their
runtimes (sections 4 and 5): `thread/start` opens a session, `turn/start` sends a prompt, `turn/steer` a steer,
`turn/interrupt` a cancel; their stream becomes `turn/started`, `item/started`, `item/agentMessage/delta`,
`item/completed` and `turn/completed` with the item shapes the view model already validates; a call to edi's tool
server becomes an `item/tool/call` server request and its answer goes back to the tool server;
`request_user_input` becomes `item/tool/requestUserInput`. Their `threadPolicy()` states what is true of them: no
sandbox escape is possible because no command or file tool exists, approval policy `never` because every permission
request is declined, and their own model provider (`anthropic`, `github`). A provider never claims a field it cannot
show; one it has no equivalent for is absent from both its policy and its readback, and the view model compares only
the fields the policy names. The translator answers `thread/start` and `thread/resume` only after the session reports
positive evidence, from the runtime process that will receive the thread's input, of its effective tool set and its
identity (sections 4 and 5), and edi's tool server has answered that process's `tools/list`. Missing evidence, a tool
the admitted catalogue does not hold, or an admitted tool the runtime does not show is an error before any user input
is written; the error carries the expected and the observed sets, so the view model's diagnostics show both. So the
view model's existing policy check (`policy_current()`) and the admission order in `native_dispatch` stay as they are
for every provider, and every new process (a new thread, a resume, a restart for another effort) repeats the evidence
before its first input. Methods a runtime has no equivalent for (the thread browser, usage where the provider has
none) are answered with the error states the view model already shows.

**ChatGPT through the direct connection, second.** `NativeChatGptProvider` (`app/src/native_chatgpt_provider.*`)
owns the `ChatGptConnection` the `NativeDependencies` constructors build, with ADR-0056's credential handling
unchanged. It offers that path's own operations through the interface (`signIn`, `send`, `cancel`, `signOut`,
`state`, `poll`), not the runtime protocol, which it refuses. The view model's `generic_mode ? … : connection->…`
switches become one test of what the active provider offers, followed by calls on that provider, in the same order as
today. Neither ChatGPT path is outside the adapter, and both behave as before.

**Activity rows keep their shape.** Saved history rows store the item payloads of edi's assistant protocol, so
presentation code and saved history files stay as they are for every provider.

### 2. One process transport

The neutral half of `CodexAgent` becomes `AssistantProcess` (`app/src/assistant_process.*`): start through the guard
(`guard <appPid> <runtime> <args…>`), newline framing with the JSON size limits, operation deadlines and their
suspension, generation fencing and `retire()`, stderr drained and never shown, and the exit-code mapping (127, 125,
128+n). `CodexAgent` keeps its API on top of it and gains one overload, `start(executable, workspace, environment)`, through
which an added ChatGPT account gets its `CODEX_HOME` (§8); the two-argument form keeps today's environment. Copilot's ACP is JSON-RPC 2.0, so `CopilotProvider` uses the same
request, response and server-request layer with the `jsonrpc` member added; Claude's stream-json is one JSON object per
line, so `ClaudeProvider` uses the framing alone. The JSON size helpers move to `app/src/assistant_json_size.hpp`
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
  name, owner-only. The bridge finds it through the server entry's environment: `EDI_ASSISTANT_TOOLS` names the
  socket and `EDI_ASSISTANT_TOOLS_FILE` an owner-only file in edi's prepared workspace holding a random key. A path
  rather than the key itself, because runtimes scrub credential-looking variables from MCP server environments, and
  never arguments, which other users can read in the process list. The bridge's first
  line is the key; the server accepts one connection per runtime process and binds it to that process's generation.
- **Lifecycle.** The server answers `initialize` with the client's `protocolVersion` when edi supports it (2025-03-26
  to 2025-11-25), otherwise 2025-11-25, and `capabilities: {tools: {listChanged: false}}`; it answers `ping`. Any other
  request, before or after `initialize` (a newer client's `server/discover` probe included), gets JSON-RPC error
  -32601 at once and the connection stays open.
- **`tools/list`** returns the catalogue the view model builds for the thread (the `dynamicTools` of its `thread/start`
  request) as `name`, `description` and `inputSchema`, plus `request_user_input` (below). MCP requires a root
  `type: "object"` and Claude refuses a root `oneOf`, `anyOf` or `allOf`, so every tool whose root carries one
  (today `set_experiment_type`, `edit_structure`, `edit_atom`, `edit_experiment`, `edit_relation`, `add_relations` and
  `edit_background`) is flattened in this projection only: the union of the branches' properties, `required` limited to
  what every branch requires, a selector as one enum, and no combinator left at the root. The exact branch check stays in `assistant_native_arguments`, which every call already
  passes. Each tool carries `_meta: {"anthropic/alwaysLoad": true, "anthropic/maxResultSizeChars": 500000}`, so
  Claude loads it up front and never moves a result to a file the model cannot read. ChatGPT's `dynamicTools` do not
  change.
- **`tools/call`** reaches the provider of the process it came through, which emits it as edi's assistant protocol
  does for Codex: a `dynamicToolCall` item for the active turn, then the `item/tool/call` server request. It enters the
  view model's existing dispatch (`native_dispatch`, the snapshot check included) like a ChatGPT call. A call with no
  running turn, after Stop, from a retired process, or before the tool set was verified (sections 4, 5) is refused by
  the provider. The reply is the same projected JSON ChatGPT receives, returned as
  `{content: [{type: "text", text: <outgoing JSON>}], isError: !success}`. `notifications/cancelled` resolves the
  server request the way Codex's `serverRequest/resolved` does.
- **Questions.** `request_user_input` is edi's question tool for Claude and Copilot, with the schema of Codex's tool of
  the same name (at most three questions, options to click, a free answer). The provider emits a call as
  `item/tool/requestUserInput`, so it becomes the question card Codex's questions use today, and the answer is the tool
  result. edi's instructions already name the tool, so the
  same text serves every provider. The runtimes' own question tools stay off (sections 4, 5).
- **Names.** The server is called `edi`; the models see `mcp__edi__<tool>` (Claude) and `edi-<tool>` (Copilot).
- **Timeouts.** A fit or a question can outlast a runtime's default MCP call timeout. Each runtime's config gives edi's
  server one fixed number, one day plus a minute, since edi sets no total limit on a fit or a question (section 4:
  `MCP_TOOL_TIMEOUT`; section 5: the entry's `timeout`), and while native work runs the server sends
  `notifications/progress` every 30 seconds for a call that carried a `progressToken`, so an idle window never cuts a
  long fit.

The guard, the catalogue and the dispatcher stay one implementation for all three providers.

### 4. Claude

One long-lived process per open thread, started through the guard in edi's prepared workspace:

```
claude -p --input-format stream-json --output-format stream-json --verbose --include-partial-messages
  --mcp-config <workspace>/.edi/claude-mcp.json --strict-mcp-config
  --tools "Skill" --allowedTools "mcp__edi__*,Skill"
  --setting-sources local --plugin-dir <workspace>/.edi/claude-plugin
  --model <id> [--effort <level>] (--session-id <new uuid> | --resume <uuid>)
  --append-system-prompt-file <workspace>/.edi/instructions.md --system-prompt-snapshot off
```

- **Tools.** `--tools "Skill"` leaves one built-in tool, the skill loader the bundled skills need; command, file,
  web, agent and question tools are off. `--tools` does not govern MCP tools, so `--strict-mcp-config` with one config
  holding only edi's server is what limits them. `--allowedTools` pre-allows edi's tools and the loader; any other
  permission request is denied, since `-p` has nobody to ask and no permission prompt tool is named.
- **Settings.** No user or project settings load: `--setting-sources local` reads only
  `<workspace>/.claude/settings.local.json`, which edi's prepared workspace never contains (a present one refuses
  the start). So no hooks, MCP servers or `CLAUDE.md` from elsewhere apply: a settings file can add hooks and servers
  that run outside the tool policy. The authentication methods that work in edi are therefore the binary's own login
  in the account's home and the credentials of the environment (key, token, cloud provider); a method kept only in a
  settings file (`apiKeyHelper`, a settings `env` block) is not loaded, and the Account dialog says so when the
  runtime reports no credential. This keeps the user's own API key, through the environment, and does not open the
  tool policy. Whether a settings-only method must also work is a scope question for the owner (open question 2
  below); until it is answered the boundary above holds.
- **Managed settings.** An organisation's managed Claude settings (a managed settings file, a device-management
  policy, or settings Anthropic's servers deliver to an organisation's accounts) always apply and edi does not disable
  them; their hooks are the organisation's own controls, chosen by its administrator for every Claude session on the
  computer, and run outside edi's tool boundary by that choice. They cannot be prevented while managed policy is
  respected, and settings delivered by Anthropic's servers cannot be seen before a launch, so edi asks before any
  launch rather than after an observation: the consent the user gives before Claude's first sign-in, which every later
  start and resume of that account relies on, says that an organisation managing Claude can run its own commands when
  Claude starts and before each message, outside edi's tools. That consent covers policy edi has not seen and policy
  that changes later. On top of it, when a managed settings file or policy is visible at the documented locations,
  or the stream's `hook_started` events before `system/init` show a hook ran, the account says so and Send waits for
  the user's acknowledgement, once per account. Whether this consent is enough to cover managed effects is open
  question 3; until the owner answers, it is what edi does.
- **Environment.** `CLAUDE_CONFIG_DIR=<account home>`, `DISABLE_UPDATES=1`, `MCP_TOOL_TIMEOUT` (§3),
  `MCP_PROTOCOL_NEGOTIATION=legacy`. Removed, because they change how edi's tools and turns run: `CLAUDECODE`,
  `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` and `CLAUDE_AUTO_BACKGROUND_TASKS`. Anthropic's conditions for shipping Claude Code
  name the user's own API key among the methods a product may not restrict, so edi keeps the user's own credential and
  provider variables (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_BASE_URL`,
  the cloud-provider switches and the like) and the user's Anthropic profile folder. When one of them decides the
  identity, the Account dialog says that Claude is using it (the readback below), and no turn runs before the
  readback matches what the dialog shows. edi itself offers only the subscription sign-in and never asks for, stores
  or injects a key.
- **Sign-in and sign-out** run the binary's own `claude auth login` and `claude auth logout` with the account's
  `CLAUDE_CONFIG_DIR`, with no flag that picks or removes a method: the binary's login screen keeps every method it
  has, and edi sets no `forceLoginMethod` or other setting that restricts one. edi opens the URL the binary prints only
  when it is `https`, carries no user info and is on Anthropic's sign-in hosts (`claude.ai`, `claude.com`,
  `anthropic.com` and their subdomains, checked against the pinned binary in the owner's trial), the same shape as
  ChatGPT's check. When the binary asks for a code, edi shows a field and writes what the user types only to the
  sign-in process's input; it never stores, logs or records it. edi offers no API-key entry of its own.
- **Identity readback, before any input.** The identity that gates Send comes from the turn process itself, so the
  probe and the turn cannot disagree: its `initialize` reply's `account` (e-mail, organisation, subscription type,
  token source) and its `system/init` `apiKeySource`. `claude auth status`, run with the same environment, working
  folder and config home, only decides whether to offer sign-in (`authMethod: none`) and checks `configDirectory`
  against the account's home. The account record keeps the non-secret principal the user saw: provider `anthropic`,
  the method and source (`claude.ai` login, `ANTHROPIC_API_KEY`, a token, a cloud provider) and the e-mail and
  organisation when the runtime gives them. Only an e-mail names the person; an organisation, a method or a key's
  source does not, since many credentials share them. A credential for which the runtime names no e-mail (a key or
  token, with or without an organisation) is an **unidentified credential**: the dialog says that Claude is using a key from the
  environment, without showing it, and the account is never matched to a verified record. Conversations started under
  it are kept as history but never resumed in a later process, because nothing proves the same credential is back; a
  new process starts a new conversation, and a verified account's thread never runs under it. Every process start repeats the readback before its first input; a missing field the record holds, or a
  different value, stops Send with the reason shown and marks the account as needing attention, for a new thread and
  for a resumed one alike. edi never opens a file inside the home.
- **Tool and skill readback, before any input.** The documented stream sends `system/init` as its first event, before
  any input; edi waits for it, within the start deadline, and writes no user message until it has passed. Its `tools`
  must equal exactly `Skill` plus `mcp__edi__<name>` for each tool of the admitted catalogue (and
  `request_user_input`), with nothing missing and nothing extra; `mcp_servers` must be exactly `edi`, connected;
  `plugins` exactly edi's; `skills` (and the `initialize` reply's `commands`) must list each bundled skill as
  `edi:<id>`. No `system/init` before the deadline fails the start; there is no path that sends input first. A pinned
  release that does not send it before input cannot be pinned.
- **Skills.** The same approved skill bytes as ADR-0058's `.agents/skills` are staged as a plugin,
  `<workspace>/.edi/claude-plugin/.claude-plugin/plugin.json` naming `edi` plus `skills/<id>/SKILL.md`. Plugin skills
  load from `--plugin-dir` independently of setting sources.
- **Turns.** `initialize` first; a turn is one `user` message whose `uuid` is edi's client message id. Its first text
  block is a one-line edi header, so a user message starting with `/` reaches the model as text and never runs as one
  of the binary's commands. A message sent during a turn is a steer. Stop sends the `interrupt` control request, with
  `cancel_queued: true` when `system/init` lists the `interrupt_cancel_queued_v1` capability, and edi checks the receipt
  so a steer queued before Stop does not start a new turn. The turn ends at `result`; edi checks
  `is_error` and the assistant message's `error`, not only `subtype`, because a signed-out turn reports `success`
  with `is_error: true`.
- **Models** come from the `initialize` reply (`value`, `displayName`, `supportedEffortLevels`). A model change during
  a thread uses `set_model`; an effort change restarts the idle process with `--resume` before the next turn. For a
  model with no advertised default effort, an empty effort means edi passes no `--effort` (an amendment of ADR-0057,
  §14).
- **Usage.** `rate_limit_event` is a status signal sent when a limit's status changes, not a per-turn feed. A window
  shows only when the event carries `rate_limit_type` and `utilization`: `five_hour` as the session limit and
  `seven_day` as the weekly limit, the windows ChatGPT already shows; other types are ignored. A warning or refusal
  with its reset time shows as it is, and "Unavailable" is the normal state between events.
- **Threads.** edi chooses the session id. A resumed thread starts a new process with `--resume`; its earlier rows come
  from edi's own history file, and `--system-prompt-snapshot off` makes it read edi's current instructions and skills.
- **Version.** One pinned release. Every pin change repeats the owner's sign-in trial.

Product text says "Claude"; "Claude Code" appears only in notices and in docs that say what edi runs.

### 5. GitHub Copilot

One process per active account, one ACP session per thread:

```
copilot --acp --stdio --no-auto-update --disable-builtin-mcps --disable-mcp-server computer-use
  --available-tools "skill,edi-<tool>,…" --allow-tool skill --allow-tool edi
  --additional-mcp-config @<workspace>/.edi/copilot-mcp.json
```

- **Tools.** `--available-tools` is a closed list: `skill`, the loader the bundled skills need, and `edi-<name>` for
  each tool of the admitted catalogue, so shell, file, web fetch, agents and Copilot's own question tool are not
  available at all; the
  built-in MCP servers (GitHub's, which serves `web_search`, and `computer-use`) are off, so Copilot has no web search;
  edi's server is the only MCP server and its tools are pre-allowed. edi never sets `--allow-all`, `--yolo`,
  `COPILOT_ALLOW_ALL` or the autopilot mode.
- **Environment**, built from an allow-list rather than the app's environment: the platform's basic variables (path,
  home, temporary folder, locale, system folders) and proxy and certificate settings, plus what edi sets:
  `COPILOT_HOME=<account home>`, `COPILOT_AUTO_UPDATE=false`, `COPILOT_SKILLS_DIRS=<workspace>/.agents/skills`,
  `COPILOT_LARGE_OUTPUT_THRESHOLD_BYTES` at edi's outgoing result bound (the default 20 KiB would move a larger result
  to a file the model cannot open), and `GH_CONFIG_DIR` pointing at an empty edi-owned folder so the CLI finds no `gh`
  login. So the child never gets `COPILOT_GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN`, `GH_HOST`, `COPILOT_GH_HOST`,
  `COPILOT_ALLOW_ALL`, `COPILOT_MODEL`, the provider overrides or instruction folders from elsewhere. The CLI also reads
  personal skills from `~/.agents/skills`; edi checks that the bundled skills are present and does not claim others
  absent.
- **edi's tools** come through `--additional-mcp-config` as `{type: "local", command, args: ["mcp"], env,
  tools: ["*"], timeout, deferTools: "never", disableToolCache: true}`: all of edi's tools, loaded up front, from live
  discovery rather than an earlier session's snapshot, with §3's timeout; ACP's `session/new` server entry has no
  timeout.
- **Protocol.** JSON-RPC 2.0 over stdio. `initialize` with `protocolVersion: 1` and client capabilities naming no
  `fs` and no `terminal`; `session/new` with the workspace as `cwd`; then `session/set_config_option` for the model,
  and for the effort when one is chosen. `session/prompt` runs a turn and `session/update` streams it; a message sent
  during a turn waits in edi's queue. Stop sends `session/cancel` and answers every open permission request
  `cancelled`. Resume uses `session/load`; its replayed updates are not shown again, because edi's history file
  holds the rows. A thread is recorded once its first turn ends, since the CLI saves no session without a turn.
- **Permissions.** Every `session/request_permission` is answered by selecting the offered option whose `kind` is
  `reject_once`, else `reject_always`, else with outcome `cancelled`; never a JSON-RPC error. Every
  `elicitation/create` is declined; questions come through `request_user_input`.
- **Tool and skill readback, before any input.** ACP and the CLI document no readback of a session's effective tool
  set, so Copilot's evidence is weaker than Claude's, and edi says so rather than claiming more. Before the first
  prompt of a session edi requires: the closed `--available-tools` list it launched the process with, its tool server
  having answered that process's `tools/list`, and `available_commands_update` listing each bundled skill. Two
  controls act before any effect: a tool outside `--allow-tool` must ask through `session/request_permission`, which
  edi always declines, and a `tool_call` update for a tool outside the closed list stops the turn and retires the
  process. Each pin's owner trial asks a session to run a shell command and to read a file and records that both are
  refused; a pin where either acts is not shipped. If the CLI gains a documented readback of the effective tool set,
  edi requires it like Claude's. These are intended settings and enforcement, not an observation of the effective
  set, so they do not meet §1's evidence rule by themselves: until the owner rules on it (open question 1 below) or
  a pinned CLI supplies an observation, a Copilot session never receives user input. The Copilot provider is built
  and tested, and the Account dialog shows it as not yet available.
- **Instructions.** edi writes its instructions to `AGENTS.md` in the workspace, the CLI's custom instructions file.
  Each prompt starts with the same one-line edi header as Claude's, so a message starting with `/` is never run as one
  of the CLI's commands.
- **Sign-in** runs `copilot login [--host https://<name>.ghe.com]` with the account's `COPILOT_HOME` and the empty
  `GH_CONFIG_DIR`. edi shows the lines the CLI prints (the URL and the device code) with an Open button, offered only
  for `https://github.com/login/device` or the account's own `https://<name>.ghe.com` host; exit code 0 is success. If the CLI asks to keep the token in a plain file because no system keychain exists, edi shows the
  question with Yes and No, No by default.
- **Identity readback, before any input.** The login lives in the OS keychain, not in `COPILOT_HOME`, and choosing a
  home does not choose which keychain identity the CLI uses. The provider observation is the CLI's account command,
  `/user` ("Manage signed-in accounts"): when `available_commands_update` advertises it, edi selects the record's
  login with `/user switch <login>` in the session that will receive the input and reads it back with `/user show` in
  that same session, before its first prompt and again after every process start and `session/load`. Send and resume
  require a positive match of both the login and the host (`github.com`, or the account's `<name>.ghe.com`); a failed
  switch, an absent, unreadable or different login or host stops Send with the reason shown. The pinned CLI (1.0.116)
  documents `/user` for its interactive interface but does not promise it over ACP, and an unauthenticated session
  does not show the advertised commands, so whether it qualifies is checked in the owner's trial. Without an
  advertised `/user` there is no selection and no identity proof, and Copilot sessions never receive input or resume.
- **No seat, organisation policy, signed out.** `-32000` on `session/new` means signed out. Any other refusal shows
  the CLI's message as it is, plus any `notice` update. A server whose `tools/list` never arrives shows that the
  organisation's policy may block edi's tools.
- **Sign-out.** ACP's `logout` (advertised by the pinned CLI in `agentCapabilities.auth.logout`) takes no account and
  ends the process's current authentication; it does not by itself prove that the selected keychain identity is gone
  while another stays. So edi does not offer Sign out for Copilot until a pinned CLI is qualified in the owner's trial:
  with two accounts on one host, signing one out leaves it signed out after a fresh start and leaves the other
  available. Until then the action is "Remove from edi": edi stops the process and deletes the home folder it created
  (the one operation in which edi changes a runtime's files, since the CLI keeps a plain-text token there when no
  keychain exists), drops the account's record, and says plainly that the GitHub sign-in stays in the system keychain
  until it is removed there or revoked on GitHub.
- **Usage** is not reported (`Unsupported`, an existing state).
- **Version.** One pinned release, 1.0.115 or newer (1.0.105 fixed skipped permission requests; 1.0.115 sends
  questions as ACP elicitations, which edi declines in favour of `request_user_input`). Copilot on Linux needs the
  system's OpenSSL 3.

### 6. What a runtime may do

The same rule for all three: the runtime's own tools that read or write files, run commands, fetch the web or start
agents are off; edi's tools, edi's question tool and the skill loader are on (ChatGPT's hosted `web_search` stays as
ADR-0057 has it); every other permission request is declined; no runtime updates itself; the working folder is edi's
prepared workspace. A runtime writes only inside its config home, its cache and the OS credential store. The first
ChatGPT account keeps ADR-0057's caveat: its runtime runs in the user's default Codex home and reads the user's own
Codex configuration there, which edi does not claim to confine.

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
  and selection. Every thread record edi writes from now on names its `account`; a record without one is a legacy
  record whose owner edi resolves from its saved e-mail (below).
- **Homes.** Each account except the first ChatGPT one gets `<AppLocalData>/assistant/accounts/<provider>/<id>`,
  created empty by edi, owner-only on POSIX, and given to the runtime as `CODEX_HOME`, `CLAUDE_CONFIG_DIR` or
  `COPILOT_HOME`. edi never opens anything inside it, and never adopts `~/.claude` or `~/.copilot`.
- **The existing ChatGPT login.** The first ChatGPT account has `home: ""`: `CODEX_HOME` stays unset and the runtime
  starts with today's environment, so nobody signs in again. Its record is written the first time `account/read` in the
  default home returns a ChatGPT account, with that e-mail. A legacy thread record (no `account`) belongs to the
  default-home record whose e-mail equals the thread's saved, independently verified e-mail; a legacy record with no
  saved e-mail, or whose e-mail no default-home record holds, stays unbound: it is listed as belonging to an account
  edi has not recorded (its e-mail shown when known), no switch is offered, and opening it fails with ADR-0057's
  identity error as today. So the first start after an upgrade, with the default login already changed from A to B,
  records B and leaves A's threads unbound until A's login is back, when A's record is written and they resolve to it.
- **Threads.** Each record names its provider and account. The thread browser lists the active account's threads:
  ChatGPT's from the runtime as today, Claude's and Copilot's from edi's records. Opening a saved thread whose record
  names another account than the active one says "This conversation belongs to <account> (<provider>)" with Switch
  account and Cancel, in place of the check of the saved record against the current account before anything opens.
  ADR-0057's identity checks after that (the live account's identity, the preflight and resume comparisons) stay
  errors with today's wording, per account home. A home that reports another identity than its record is an error;
  edi never relabels the record. The default ChatGPT login is the user's own Codex login, which can change outside edi:
  when the default home reports another e-mail than its record, edi does not relabel that record but adds a new
  default-home record with a new id for the new identity and makes it active. The old record, and every thread that
  belongs to it (legacy records resolved by their saved e-mail included), keeps its original identity, so opening one of them offers
  to switch to the old record, whose own readback then fails with ADR-0057's identity error until the user signs the
  default login back in as the original account. The saved e-mail of each thread record stays the independent check
  at listing, opening and resume, as ADR-0057 has it. Adding an account whose user and host are already recorded is
  refused, and its new home is deleted.
- **Switching** retires the current process as sign-out does, without logging out, advances the usage epoch every
  queued reply already checks, starts the other account's runtime and opens an empty conversation. It is refused while
  a turn or trial runs, with Clear's rule and wording.
- **Private roots.** Beside today's roots, the file tools refuse the new runtimes' credential stores: `~/.claude`,
  `~/.claude.json`, `$CLAUDE_CONFIG_DIR`, the Anthropic profile folder (`~/.config/anthropic`, `%APPDATA%\Anthropic` or
  `$ANTHROPIC_CONFIG_DIR`), `~/.copilot`, `$COPILOT_HOME`, and the `gh` folder (`~/.config/gh`, `$XDG_CONFIG_HOME/gh`,
  `%APPDATA%\GitHub CLI` or `$GH_CONFIG_DIR`). The account homes under `<AppLocalData>/assistant/accounts` are already
  covered by the app-data check.

### 9. The Account dialog

The account button (`connectionButton`) keeps its place, size and states, and keeps opening the Account dialog
(`accountDialog`, ADR-0057's account card); it stays the one account surface. The dialog gains one group per provider:
a header with the provider's name, one row per account with the active one checked and its e-mail, plan and state, a
Switch action on the others, Sign out (for Copilot, Remove from edi) on the active account, and "Add account" per installed provider (disabled,
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
component, as ADR-0071 says, with one exception: the Claude component is distributed only when enhantica's acceptance
of Anthropic's Commercial Terms is recorded. One committed eligibility setting in the release configuration decides it,
and every distribution route reads that one setting: the offline installers' bundled payload, the public component
repositories and their publication, and the installer's and the Maintenance Tool's selection. While it is off, the
Claude component is built and tested internally, its archive stays out of every public artifact, and the installer
shows no Claude checkbox. The release steps that name the component set (publication, the download site's trim list and
size budget, the Windows runtime scan, the accessibility check) learn the new components. The download site refuses a
file over 100 MB and publication caps an archive at 95 MB, so each new component's archive size is measured per
platform at the pinned version before the installer work; an archive over the cap needs the owner's choice of host or
packaging, recorded here.

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
- ADR-0057's effort rule ("Auto effort sends the model catalogue's actual supported default explicitly"): for a Claude
  model that advertises no default, an empty effort means edi passes no effort (§4).
- ADR-0023 §6: the web app's desktop-only message names ChatGPT, Claude and GitHub Copilot.
- ADR-0071, "Optional assistant component": the single checkbox becomes three components (§11).
- ADR-0071's rule that offline installers bundle every component: the Claude component is bundled and published only
  once the acceptance of Anthropic's Commercial Terms is recorded (§11).
- ADR-0057's account scope: the check of a saved conversation against the current account before it opens compares
  account ids first, then the saved e-mail as before; a changed default ChatGPT login becomes a new account record, so a
  thread never moves to another identity (§8).
- ADR-0091, "What is signed": the runtime helpers it signs are Codex's; the Claude and Copilot binaries are not signed
  (§12).

### 15. Out of scope

The web app (ADR-0023 §6); an API-key entry of edi's own; GitHub Enterprise Server, which the Copilot CLI reaches only
with a token in the environment; voice input; new tools; Copilot's bring-your-own-key providers.

## Open questions for the owner

The vendors' current runtimes cannot supply three observations this design asks for; each question names the route it
holds closed until it is answered, and the course this ADR recommends.

1. **GitHub Copilot's tools.** Neither ACP nor the pinned CLI documents a readback of a session's effective tool
   set. Until a substitute is accepted, or the Copilot route is dropped, Copilot sessions receive no
   input; the code holds this in one constant (`assistant_copilot_input_open`). Recommended: accept for Copilot the
   documented server-start filter (`--available-tools`, "the session can use only the listed tools"), with permission
   denial, as its tool control. Accounts are not part of the question: Send and resume always need the positive
   login-and-host match above, and a pin without `/user` over ACP offers no Copilot input at all. A `tool_call`
   outside the closed list is detection, not a veto, since ACP notifications cannot stop a call.
2. **Claude credentials kept only in settings** (`apiKeyHelper`). Recommended: unsupported in edi; the user's own key
   works through the environment.
3. **Claude managed hooks.** An organisation's managed hooks cannot be prevented while managed policy is respected.
   Recommended: the consent before the first sign-in plus the per-account acknowledgement in §4.

Copilot's Sign out is not an owner question but a pin qualification (§5): until the owner's trial shows a selected
account stays signed out after a fresh start while another stays available, only "Remove from edi" is offered.

## Consequences

- A fourth runtime is one more `AssistantProvider`, package and component; the tools, dispatcher and history stay.
- The view model keeps the app-server vocabulary as edi's protocol, so both ChatGPT paths behave as before, and each
  new runtime pays for a translation that must produce the lifecycle the view model already validates.
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
| A new neutral protocol, with every Codex payload moved out of the view model | Rejected for now: thousands of lines of fenced, order-sensitive code moved at once, with no visible gain and a real risk to ChatGPT's behaviour. |
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
