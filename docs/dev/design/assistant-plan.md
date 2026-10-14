# In app assistant implementation plan

Draft for discussion. The assistant should take a request such as “convert this FullProf project and fit it”,
inspect the inputs, propose a plan, run agreed refinement steps, recover from unsuccessful trials, and save a
reproducible edi project. It should also answer questions about the open project and teach edi workflows.

## Existing design and implementation

The existing assistant roadmap proposes project context, diagnostic suggestions, what-if previews and guided
workflows. This proposal extends that design with account connections, chat, executable skills and optional
automatic refinement after the user agrees a plan. The execution policy needs an explicit decision before it
replaces the existing proposal-only behaviour.

Prior implementations to extend:

- `app/qml/Main.qml` owns the application shell and project actions.
- `app/qml/Components/WorkflowPage.qml` places the workflow sidebar using `Preferences.sideBarSide`.
- `app/qml/Globals/Preferences.qml` and `Components/AppPreferencesDialog.qml` own persistent app preferences.
- `core/include/edi/edit.hpp` provides project edits; `app/src/project_view_model.*` owns app undo history.
- `core/include/edi/fit_job.hpp` provides asynchronous fitting, progress, cancellation and guarded publication.
- `core/include/edi/io.hpp` provides single-level fit restoration. This needs extending for assistant trials.
- ADRs 0009, 0020, 0024, 0031 and 0034 establish the shared C++ core, worker, edits, preferences and correlations.

Product decisions and orchestration belong in the Qt-free C++ core, with thin app and transport adapters.
Scientific calculations remain in crysta. New import and checkpoint facilities must serve manual workflows and
the assistant through the same implementation. Record the resulting contracts in ADRs before production changes.

## Delivery sequence

1. **Resolve the product and provider decisions.** Choose desktop/browser coverage, authentication, the initial
   import scope, and the boundary between automatic refinement and questions for the user. Define representative
   acceptance projects and an execution contract before implementing the controller.

2. **Add the assistant sidebar and preferences.** Use a persistent panel opposite the workflow sidebar. Swapping
   sides in preferences moves both panels together. Include resizing, hide/show, keyboard access, streaming chat,
   conversation history, attachments, model and supported effort selectors, cancellation, retry, and readable
   connection errors. Keep conversation state across workflow tabs. Check narrow windows, theme changes,
   accessibility, preference reset and relaunch persistence.

3. **Connect Claude and expose project tools.** Establish an authenticated provider connection with explicit
   model capabilities. Store credentials outside projects, chat history and ordinary settings. Provide structured
   tools to inspect the project and diagnostics, propose and apply validated edits, calculate, fit, cancel,
   checkpoint, restore and save. Run tools against the same live project the user sees. Validate arguments,
   project identity and revision before mutations; pause when a manual edit invalidates a pending step.

4. **Ship an executable skill library.** Start with opening and saving edi projects, assembling datasets and a
   structure, importing FullProf, importing GSAS-II, staged refinement, diagnosing correlations and producing a
   refinement report. Each skill declares its supported inputs, prerequisites, tool permissions, workflow,
   scientific references and success criteria. Skills use tested tools; prose alone cannot supply a missing
   converter. Keep shipped assistant skills as product resources, separate from repository agent instructions.

5. **Implement refinement trials and recovery.** Capture a baseline and named checkpoints, then execute a
   problem-specific sequence of parameter groups. After each trial inspect fit status, comparable residuals,
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

A run stops on the agreed convergence criteria, an explicit user stop, exhaustion of its time/cost/trial budget,
or a scientific question needing user input. It returns the best accepted state and explains unresolved issues.
The interface must distinguish optimizer convergence, fit quality and scientific validity; it cannot promise
that every supplied model will converge or be identifiable.

Checkpoints must restore parameter values, uncertainties, free flags, relations, fit results and associated
project files. Keep trial data separate from the original input. Define how assistant rollback composes with
the existing app undo history and survives interruption before implementing it.

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

## Authentication decision

Anthropic's documentation checked on 2026-10-14 gives conflicting guidance. Its
[Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) says third-party products need prior
approval to offer claude.ai login and directs developers to API-key authentication. Its
[subscription help page](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
says Agent SDK and third-party app usage can still draw on subscription limits. Establish the supported product
integration before promising subscription sign-in. API-key authentication is the proposed baseline; a
subscription connection must use a supported flow without collecting the user's Claude password or copying
credentials from another app.

Desktop and browser transport choices need separate consideration. A browser cannot launch a local SDK
process, and a hosted connection introduces a service and credential boundary. Keep the project tool protocol
and refinement policy shared across both targets. Model and effort choices must follow provider capabilities;
see Anthropic's [effort documentation](https://platform.claude.com/docs/en/build-with-claude/effort).

## Open product questions

- Where should the first version work: desktop, browser or both? What hosted infrastructure is acceptable?
- Which account experience is essential: Claude subscription, Anthropic API key or both? Should OpenAI follow?
- What can run automatically after the user agrees a plan? Which scientific decisions require another question?
- Which FullProf and GSAS-II project types should define initial acceptance, including joint and scan cases?
- Should chats be local app history, travel with the project, or offer both? Are user-authored skills needed initially?

## Branch provenance

Created from fetched `origin/dev` at `b713744be7d6c0ce3a6d31670ab14640f3b48d35` on 2026-10-14 using
`git worktree add -b feat/ai-assistant`. The existing `dev` checkout remains available for other development.
