# The assistant desktop candidate

Use the robot button in the app bar to show or hide the Assistant. It slides over the existing manual sidebar, on the same side and within the same bounds. The chart and main workspace keep their size. Hiding it preserves the manual controls, conversation, draft and active work; it does not cancel a fit. The panel starts closed each session. The app-bar button is its only show/hide control.

Choose **Sign in** beside **Clear**, review the readable outgoing-context summary, then continue to OpenAI's sign-in page in your system browser. **Show exact outgoing context** opens the optional technical details; approving the summary covers that same complete context. Use your own ChatGPT account and review the consent there. Messages and selected project metadata go to OpenAI; subscription availability and usage limits depend on your account. This candidate uses subscription access and does not ask for an API key. Native builds include a pinned official Codex app-server and use its ordinary managed ChatGPT sign-in. No separate CLI installation or PATH setup is needed; Edi does not copy its credentials. Browser AI remains unavailable.

Before sign-in and model discovery, the selector shows **Effort**. After connecting, choose an available model and reasoning effort; it shows the selected name. **Auto** lets the model or provider choose the reasoning effort. The candidate remembers your last model/effort pair in Edi's application settings and restores it only when the provider's current catalog supports it. Sign-out, Clear and a temporary empty catalog do not replace that preference with an automatic fallback. An unavailable saved choice uses a visible fallback; inspect it before sending.

Use **+** to select local files before connecting or while idle. Changing the collection retires the current runtime workspace; reconnect to stage the new collection. Actual selected names and byte counts appear above the draft; each item has a remove control. Native file drops onto the chat area use the same bounded intake. Desktop chooser backend and multiple-selection gestures are still being qualified; adding files through repeated chooser selections and grouped native file drops are distinct routes. Folder intake and browser file transfer remain unfinished. A typed path does not add an immutable selected input. The generic runtime’s ordinary file tools may read paths allowed by its effective policy; use selection to disclose and stage the intended inputs. Selection alone does not import data, create a project or run a fit.

Outgoing consent includes the project/selected-file manifest and the generic runtime’s working-copy authority. Selected snapshots are staged as actual workspace files; they are not fabricated uploads or a full prompt dump. Binary or unsupported formats need a supported text export; selected content is data, not instructions. Live provider use of these inputs still needs verification.

Ask about the project and inspect any proposed plan. Approval covers its displayed parameter groups and trial budget. Stop cancels the active assistant work; manual changes invalidate an old approval. Trials use a separate project copy, and an unverified or worse result is not automatically adopted. Existing manual fitting remains available. During an active generic-agent turn, submitting a draft uses the actual turn’s steer operation. Its admitted user row is retained; uncertain or refused input is not automatically retried. A message sent while the assistant runs a fit or another app action waits above the message box and is sent, in order, once that action has finished; its × control takes it back into the message box. A waiting message is never sent into another conversation: if the conversation changes first, or the message is refused when its turn comes, it returns to the message box with the reason shown. Stop stays accessible beside Send while a draft is present.

The chevrons inside the composer browse previous or next user messages. Send/Stop is the rightmost monochrome action; it shares the plus button’s size. Conversation overflow uses the same noninteractive scroll indicator as the manual sidebar; scroll the conversation normally. The neutral usage ring opens details, but this connection does not currently supply context-window or subscription-limit metrics. No percentage is inferred from conversation length or elapsed time.

Conversation activity is saved separately from the project on this computer. **Clear** retires the assistant conversation and selected inputs, removes its archive and starts fresh; it does not clear the scientific project or sign you out. Sign out asks the official runtime to sign out of its managed account. The displayed archive is not automatically sent in a new app session.

This is an implementation candidate, not a verified live-subscription release. The generic runtime uses an owned project/file working copy with workspace writes and network disabled; it declines broader approval requests. Its inherited runtime configuration remains effective: this is not a private read jail or proof that external extensions share that boundary. Nothing is automatically published back into the open project. Successful live chat, streamed inspection and an approved mutation still need verification. Decoder failure details preserve the available bounded reason and original category; diagnostics alone do not fix the failed request. Native Claude, the computer-browser connector, folder/browser file intake, complete sequential optimization and FullProf/GSAS-II import remain unfinished. A screenshot labelled SAMPLE shows original local preview text, not a live provider exchange or a completed refinement.


## ChatGPT, Claude or GitHub Copilot

The desktop assistant works with any of three providers. The installer offers each provider this release includes
as its own checkbox (ChatGPT is ticked by default); add or remove one later with the Maintenance Tool and restart the
app. Each provider runs its own
program, bundled with the app, and signs you in its own way. Edi never sees your password or tokens and offers no
API-key entry.

- **ChatGPT** signs in through OpenAI's page in your browser with your ChatGPT plan. If you already use the Codex
  command-line tool, the app starts with that login, and signing out in the app also signs it out there.
- **Claude** signs in through Claude's own login in your browser, with your Claude plan, or uses your own Anthropic
  key when one is set in your environment; the Account dialog says so. **Usage** shows your plan's session and weekly
  limits; a key has none to show. A key helper (`apiKeyHelper`) or an `env`
  block in Claude's settings file is not used; set the key in your environment instead. If the sign-in page shows a
  code, paste it into the field the app shows. Anthropic's Consumer Terms apply to Free, Pro, Max and Ultra plans, and its Commercial Terms to
  Team, Enterprise and API accounts. If your organisation manages Claude, its settings can run their own commands
  when Claude starts and before each message; when the app finds such settings it says so before you sign in, and it
  asks you once when it sees them run.
- **GitHub Copilot** signs in with GitHub's own login. Personal and business seats are meant to work, as are GitHub
  Enterprise Cloud hosts with data residency (`<name>.ghe.com`, entered when you add the account); GitHub Enterprise
  Server is not supported. GitHub's page asks for a code; the app shows it with a Copy button. Before each
  conversation the app checks that Copilot uses the GitHub account you chose. "Remove from edi" removes a Copilot
  account from the app; the GitHub sign-in stays in the system
  keychain until you remove it there or revoke it on GitHub. On Linux the Copilot program needs OpenSSL 3 from the
  system.

The account button at the top of the assistant, named after the provider, opens the **Account** dialog. It lists your
accounts by provider, each once, and marks the active one. **Add account** starts a new sign-in for that provider, **Switch** makes another account the
active one and starts an empty conversation, and **Sign out** acts on the active account (for Copilot, **Remove from
edi**). If a connection fails, the panel says so in one line with **Try again**; while an account is not connected,
**Sign out** is beside it. Each account keeps its own
conversations: opening one that belongs to another account asks whether to switch to it.

Claude and GitHub Copilot use only the app's own actions: their own file, command and web tools are off. Claude's
and Copilot's past conversations list only the ones started in this app. A Claude conversation started with a key
that names no person is kept as history but cannot be continued later.

## Try the generic desktop candidate

Build using your usual `pixi run -e app app-with-crysta ../crysta`. The normal native app build automatically downloads and verifies its app-owned runtime package. This development command also builds the existing Edi Python bindings in the compatible default environment against the same local crysta prefix, and supplies the app Python/module path to runtime commands. A plain app-only build does not establish that Python prerequisite.

Open a project, choose the robot, add intended inputs, then **Sign in** and approve the actual disclosure. After the runtime confirms the account/catalog and effective policy, send “Hello”. **Skills** is an optional inspector: all valid bundled skills are registered and the runtime loads relevant instructions on demand, without an exclusive workflow choice. Ask it to inspect selected PCR/DAT companions or a CIF/raw-data pair and identify missing scientific metadata. FullProf/GPX conversion is still unavailable. Existing Edi Python factories and CLI calc/fit/undo/report are real operations; calculation/refinement and adoption are separate, approval-bound work. Send a follow-up while a turn is running and inspect its pending/admitted row, then try Stop. These are owner smoke-test instructions, not a claim that live sign-in/inference or a complete scientific workflow was tested here.
