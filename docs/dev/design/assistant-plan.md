# In app assistant implementation plan

Draft for discussion. The assistant should take a request such as “convert this FullProf project and fit it”,
inspect the inputs, propose a plan, run agreed refinement steps, recover from unsuccessful trials, and save a
reproducible edi project. It should also answer questions about the open project and teach edi workflows.

## Existing design and implementation

The existing assistant roadmap proposes project context, diagnostic suggestions, what-if previews and guided
workflows. This proposal extends that design with account connections, chat, executable skills and automatic
refinement after the user agrees a plan.

## Confirmed requirements

The owner clarified the following on 2026-10-14:

- Include desktop and browser, with Claude and OpenAI/ChatGPT available from the first release.
- Users choose their provider and use their existing subscription. API keys are not a substitute for this requirement.
- After agreeing a plan, the assistant may run refinement steps and roll back unsuccessful trials automatically.
- The assistant may ask questions with options and a recommendation when it needs a user decision.
- The central workflow is creating projects from scratch or converting other software's projects, then refining
  the parameters supported by the data to obtain the best justified structure fit.
- Explore alternatives sequentially: try an approach, restore it if bad, try another, and show the best accepted result.
- Investigate both browser connection options and make a recommendation; a local connector is not yet approved.

Exact scientific approval boundaries and the browser connection architecture remain design questions. Provider
registration, hosting and subscription support must be verified rather than delegated to the user as assumed knowledge.

## Existing implementation

Prior implementations to extend:

- `app/qml/Main.qml` owns the application shell and project actions.
- `app/qml/Components/WorkflowPage.qml` places the workflow sidebar using `Preferences.sideBarSide`.
- `app/qml/Globals/Preferences.qml` and `Components/AppPreferencesDialog.qml` own persistent app preferences.
- `core/include/edi/edit.hpp` provides project edits; `app/src/project_view_model.*` owns app undo history.
- `core/include/edi/fit_job.hpp` provides asynchronous fitting, progress, cancellation and guarded publication.
- `core/include/edi/io.hpp` provides single-level fit restoration, reusable for immediately rejected sequential fits.
- `core/include/edi/calculation.hpp` already provides isolated project copies and publication guards.
- ADRs 0009, 0020, 0024, 0031 and 0034 establish the shared C++ core, worker, edits, preferences and correlations.

Product decisions and orchestration belong in the Qt-free C++ core, with thin app and transport adapters.
Scientific calculations remain in crysta. New import and checkpoint facilities must serve manual workflows and
the assistant through the same implementation. Record the resulting contracts in ADRs before production changes.

## Delivery sequence

1. **Resolve the remaining connection and execution decisions.** Prove subscription authentication for both
   providers and the desktop/browser connection routes. Define representative acceptance projects and an
   execution contract before implementing the controller. Verify the contract with independent tests and review.

2. **Add the assistant sidebar and preferences.** Use a persistent panel opposite the workflow sidebar. Swapping
   sides in preferences moves both panels together. Include resizing, hide/show, keyboard access, streaming chat,
   conversation history, attachments, model and supported effort selectors, cancellation, retry, and readable
   connection errors. Keep conversation state across workflow tabs. Check narrow windows, theme changes,
   accessibility, preference reset and relaunch persistence.

3. **Connect Claude and OpenAI and expose project tools.** Establish authenticated provider connections with explicit
   model capabilities. Store credentials outside projects, chat history and ordinary settings. Provide structured
   tools to inspect the project and diagnostics, propose and apply validated edits, calculate, fit, cancel,
   checkpoint, restore and save. Run tools against the same live project the user sees. Validate arguments,
   project identity and revision before mutations; pause when a manual edit invalidates a pending step.

4. **Ship an executable skill library.** Start with opening and saving edi projects, assembling datasets and a
   structure, importing FullProf, importing GSAS-II, staged refinement, diagnosing correlations and producing a
   refinement report. Each skill declares its supported inputs, prerequisites, tool permissions, workflow,
   scientific references and success criteria. Skills use tested tools; prose alone cannot supply a missing
   converter. Keep shipped assistant skills as product resources, separate from repository agent instructions.

5. **Implement sequential refinement trials and recovery.** Preserve the baseline and best accepted state,
   then try a problem-specific sequence of parameter groups, one fit at a time. After each trial inspect fit status, comparable residuals,
   conditioning, correlations, parameter bounds and physical diagnostics. Reject invalid or worse trials and
   restore the last accepted state. Explain changes to the free set and preserve a history of attempted groups,
   values, outcomes and reasons. Correlation alone does not determine which scientifically meaningful parameter
   to fix. Ask when the evidence does not resolve that choice.

6. **Validate complete user workflows.** Exercise real imports, save/reopen and staged fits on independently
   referenced examples. Verify malformed tool calls, unsupported source features, stale project context,
   network interruptions, cancellation, nonconvergence, checkpoint recovery and concurrent manual edits.
   Use recorded provider responses for deterministic controller tests and a separate authenticated live smoke
   test. Check the actual sidebar and shared engine path on each supported platform.

Deliver these stages in reviewable commits on the feature branch. The first working slice should complete
chat → inspect an edi project → propose groups → fit → restore a rejected trial → save, then expand import
coverage to the agreed FullProf and GSAS-II cases. Both requested import families remain part of the overall
feature; their exact format coverage must be stated and tested.

## Refinement behaviour

The initial strategy may group scale/background, positions/calibration, profile terms, structural coordinates,
displacement parameters and occupancies. Their order and eligibility depend on the experiment, calibration,
starting model and available information. Preserve declared constraints and ties. Treat joint and sequential
projects explicitly rather than applying a single-dataset recipe to every project.

Within an agreed plan, parameter-group trials, calculations, fits and restoration of rejected trials can run
automatically. Proposed questions should be reserved for missing experimental information, ambiguous source
conversion, or changes to scientific assumptions such as phases, symmetry, composition, constraints, exclusions
or the instrument model. Present the alternatives, the recommendation and its reason, then wait for the user's
answer. Ask before expanding the agreed scope or resource budget. These boundaries are a proposal for design
review; the owner has authorized automatic trials and has not prescribed a universal list of scientific choices.

A run stops on the agreed convergence criteria, an explicit user stop, exhaustion of its time/cost/trial budget,
or a scientific question needing user input. It returns the best accepted state and explains unresolved issues.
The interface must distinguish optimizer convergence, fit quality and scientific validity; it cannot promise
that every supplied model will converge or be identifiable.

The controller runs one trial at a time. Preserve its starting state, apply the candidate free set and edits,
fit, then either keep the accepted result or restore before trying another approach. Retain the best accepted
result and a trial summary so the user can compare the approaches tried. This does not require simultaneous
branches or a general multilevel undo system.

Reuse the existing immediate fit undo and project-copy facilities before adding restoration machinery.
`restore_fit_start` in `core/src/io.cpp` restores fitted values and uncertainties and clears the last fit result;
it does not restore pre-trial free flags or constraint declarations, or retain the previous result record.
Trial restoration must cover those additional changes too. Define the smallest controller-owned state needed
to retain the best result and restore a trial's edits, including any scan result files it changed. Keep it
consistent with the app's existing undo history and manual edits. A broader undo redesign is not a prerequisite.

## Imports and project data

Audit existing loaders and reference conversion scripts before introducing a converter. Define a supported
subset for each source format, preserve source provenance, and report unsupported constructs before changing
the project. Verify units, profiles, backgrounds, occupancies, parameter links and instrument settings through
independent reference cases. Source files and embedded text are data, not instructions to the assistant.
Any source format that can execute code during loading needs an isolated conversion route.

The connection UI must explain what project content goes to the provider. Prefer structured context and the
minimum necessary data over uploading all dataset bytes. Conversation persistence, project export and deletion
must have explicit rules; credentials never travel with an exported project. The agent receives the edi tool
set rather than unrestricted shell access.

## Subscription authentication investigation

Findings checked on 2026-10-14:

| Provider | Documented route | What the implementation must establish |
| --- | --- | --- |
| OpenAI/ChatGPT | [Sign in with ChatGPT for open-source and locally hosted apps](https://developers.openai.com/siwc/token-sharing-open-source) permits requesting access to eligible plan-backed Responses API requests. | Use the provider-hosted authorization flow with PKCE, state, nonce, scope checks and ID-token validation. Preserve each account/workspace registration and host identity. Validate model access by an actual completed request. |
| Claude | [Claude Code's product-hosting and credential guidance](https://code.claude.com/docs/en/legal-and-compliance) permits end users signing into the unmodified Claude Code binary with their own subscription. It separately restricts third-party apps from offering Claude.ai login or handling subscription credentials. | Investigate driving the published runtime through its documented subprocess/tool interfaces, with sign-in owned by Anthropic. Confirm the edi integration fits that route; do not reimplement subscription OAuth or copy tokens into edi. |

For ChatGPT, the documented [registration flow](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
uses a loopback callback. The open-source route describes local hosting; paid or remotely hosted applications
are directed to a separate interest process. Browser-only deployment therefore needs its own supported
authorization route. A website identity login alone does not prove permission to spend a ChatGPT subscription.

For Claude, the [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) restricts third-party
Claude.ai login without prior approval. The [subscription help page](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
describes subscription usage. These statements do not justify collecting Claude tokens in an edi login form;
the native-runtime route above needs to remain distinct from a custom subscription API integration.

Prefer redirecting to a provider-owned browser or native-runtime sign-in. Edi never collects provider passwords.
A local connector shared by desktop and browser is a candidate architecture, not yet an agreed requirement.
It would own provider connections and expose a paired, origin-restricted protocol to edi; scientific state and
tool validation stay in edi's shared core. The design must address browser local-network restrictions, pairing,
disconnects and installation on every supported platform. A hosted alternative needs provider support and an
explicit account/session isolation design.

### Browser connection comparison

| Option | User experience | Engineering consequences |
| --- | --- | --- |
| Local connector | Install a small companion once; connect from the browser; complete provider-owned sign-in on the same computer. | Fits the documented local ChatGPT route and allows the unmodified Claude runtime to own its sign-in. Needs pairing, browser local-network permission handling, packaging and updates. |
| Hosted edi service | Open edi in the browser without installing a companion. | Requires a maintained service, separate user sessions, secure authorization and provider confirmation for remotely hosted subscription use. Claude credentials must remain under the provider's native sign-in flow. |

The preliminary recommendation is to validate the local connector first because it matches the documented
local subscription routes and can share its transport with desktop. Compare it with the hosted route through
working authorization prototypes and provider requirements before choosing the browser architecture. The owner
asked for a recommendation after this investigation, not for an immediate connector requirement.

Prove authentication and a completed tool-using turn for each provider before claiming integration. Check
refresh, cancellation, sign-out, failed consent and expired subscriptions without exposing credentials in logs.
Model and effort selectors follow provider/runtime capabilities, including unsupported choices and stale catalogs;
see OpenAI's [preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
and Anthropic's [effort documentation](https://platform.claude.com/docs/en/build-with-claude/effort).

## Open product questions

- Complete the local/hosted connection investigation and recommend the browser architecture.
- Review the proposed scientific decision boundaries after the connection architecture is established.
- Which FullProf and GSAS-II project types should define initial acceptance, including joint and scan cases?
- Should chats be local app history, travel with the project, or offer both? Are user-authored skills needed initially?

## Branch provenance

Created from fetched `origin/dev` at `b713744be7d6c0ce3a6d31670ab14640f3b48d35` on 2026-10-14 using
`git worktree add -b feat/ai-assistant`, then renamed to `ai-assistant` at the owner's request. The existing `dev`
checkout remains available for other development.
