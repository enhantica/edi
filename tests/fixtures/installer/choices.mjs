// SPDX-License-Identifier: BSD-3-Clause
// Exercise the shipped IFW script callbacks against an observable wizard port.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {createContext, runInContext} from 'node:vm';

const root = process.argv[2];
const carriesClaude = process.argv.includes('--with-claude');
const source = name => readFileSync(join(root, name), 'utf8');
const ui = source('AssistantForm.ui');
for (const name of ['AssistantCheckBox', 'ClaudeCheckBox', 'CopilotCheckBox', 'LicenseCheckBox'])
  assert.match(ui, new RegExp('<widget class="QCheckBox" name="' + name + '"'),
    'Every install choice is an actual checkbox widget');
assert.doesNotMatch(ui, /<widget class="QTree(?:View|Widget)"/,
  'The embedded choices contain no replacement component tree');

function signal() {
  const handlers = new Set();
  return {
    connect: handler => handlers.add(handler),
    disconnect: handler => handlers.delete(handler),
    emit(...args) { for (const handler of [...handlers]) handler(...args); },
  };
}

const assistantName = 'org.easydiffraction.app.assistant';
const claudeName = 'org.easydiffraction.app.claude';
const copilotName = 'org.easydiffraction.app.copilot';
const appName = 'org.easydiffraction.app';
const selected = new Set([appName]);
const fields = {
  AppBox: {},
  AssistantBox: {},
  AssistantCheckBox: {checked: false, toggled: signal()},
  ClaudeBox: {},
  ClaudeCheckBox: {checked: false, toggled: signal()},
  ClaudeSizeLabel: {},
  CopilotBox: {},
  CopilotCheckBox: {checked: false, toggled: signal()},
  CopilotSizeLabel: {},
  FolderBox: {},
  LicenseCheckBox: {checked: false, toggled: signal()},
  LicenseLink: {},
  ShortcutBox: {},
  ShortcutCheckBox: {toggled: signal()},
  NoticeBox: {},
  NoticeLabel: {},
  SpaceLabel: {},
  TargetDirectoryLineEdit: {text: '/synthetic-target', textChanged: signal(), editingFinished: signal()},
  MessageLabel: {},
};

const frameworkPages = [
  'Introduction', 'TargetDirectory', 'ComponentSelection', 'LicenseAgreement',
  'StartMenuDirectory', 'ReadyForInstallation', 'PerformInstallation', 'Finished',
];
const pages = Object.fromEntries(frameworkPages.map(name => [name + 'Page', {
  entered: signal(), left: signal(), title: name, subTitle: '', fields: name === 'TargetDirectory' ? fields : {},
}]));
pages.DynamicAssistantForm = {
  fields: {
    AppBox: {}, AssistantBox: {}, AssistantCheckBox: {toggled: signal()}, ClaudeBox: {},
    ClaudeCheckBox: {toggled: signal()}, CopilotBox: {}, CopilotCheckBox: {toggled: signal()},
    LicenseBox: {}, ShortcutBox: {},
    NoticeBox: {}, NoticeLabel: {}, SpaceBox: {},
  },
};
pages.IntroductionPage.fields.MessageLabel = {};
pages.FinishedPage.fields.MessageLabel = {};
const summary = pages.ReadyForInstallationPage.fields = {
  InstallComponentsWidget: {visible: true},
  UninstallComponentsWidget: {visible: true},
  RemoveAllMsgLabel: {},
};
const buttonClicks = [];
const metadata = new Map();
const visibility = new Map();
const embedded = [];
const extraPages = [];
let mode = 'install';
const records = [
  [appName, 'EasyDiffraction', 123500000],
  [assistantName, 'ChatGPT', 27500000],
  ...(carriesClaude ? [[claudeName, 'Claude', 40000000]] : []),
  [copilotName, 'GitHub Copilot', 60000000],
];
const components = records.map(([name, displayName, bytes]) => ({
  name,
  value(key) { return {DisplayName: displayName, UncompressedSize: String(bytes)}[key]; },
  installationRequested: () => selected.has(name),
  uninstallationRequested: () => false,
}));

const buttons = {
  NextButton: 'Next', BackButton: 'Back', CommitButton: 'Commit', FinishButton: 'Finish', CancelButton: 'Cancel',
};
const pageIds = {
  Introduction: 'introduction', TargetDirectory: 'directory', ComponentSelection: 'components',
  LicenseCheck: 'license', StartMenuSelection: 'start-menu', ReadyForInstallation: 'ready',
  PerformInstallation: 'progress', InstallationFinished: 'done',
};
const pagesById = new Map([
  [pageIds.Introduction, pages.IntroductionPage],
  [pageIds.TargetDirectory, pages.TargetDirectoryPage],
  [pageIds.ReadyForInstallation, pages.ReadyForInstallationPage],
  [pageIds.PerformInstallation, pages.PerformInstallationPage],
  [pageIds.InstallationFinished, pages.FinishedPage],
]);
const context = createContext({
  buttons, console, systemInfo: {kernelType: 'linux'},
  QInstaller: {...pageIds, Success: 'success'},
  QMessageBox: {Yes: 'Yes'},
  Qt: {callLater: handler => queueMicrotask(handler)},
  component: {
    name: assistantName, installed: true,
    userInterface: () => mode === 'install' ? pages.TargetDirectoryPage : pages.DynamicAssistantForm,
  },
  installer: {
    status: 'success', isInstaller: () => mode === 'install',
    isUninstaller: () => mode === 'remove', isUpdater: () => mode === 'update',
    isPackageManager: () => mode === 'maintenance',
    isCommandLineInstance: () => mode === 'cli',
    hasAdminRights: () => false,
    setPackageManager() { mode = 'maintenance'; },
    setUpdater() { mode = 'update'; },
    setDefaultPageVisible(name, value) { visibility.set(name, value); },
    setMessageBoxAutomaticAnswer() {},
    environmentVariable: () => '',
    fileExists: path => path === fields.TargetDirectoryLineEdit.text,
    execute(command) {
      assert.equal(command, '/bin/df', 'Only an available-space query is required');
      return ['Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 4000000 0 4000000 0% /', 0];
    },
    executeDetached() {},
    value: (key, fallback = '') => metadata.get(key) ?? fallback,
    setValue(key, value) { metadata.set(key, value); },
    components: () => components,
    componentByName: name => components.find(entry => entry.name === name) ?? null,
    selectComponent: name => selected.add(name),
    deselectComponent: name => selected.delete(name),
    addWizardPageItem: (_component, form, page) => embedded.push([form, page]),
    addWizardPage: (_component, form, page) => extraPages.push([form, page]),
    installationFinished: signal(), updateFinished: signal(), uninstallationFinished: signal(),
    statusChanged: signal(),
    titleMessageChanged: {connect() {}},
  },
  gui: {
    showSettingsButton() {},
    setWizardPageButtonText(page, button, text) { metadata.set(page + button, text); },
    pageWidgetByObjectName: name => pages[name] ?? null,
    pageByObjectName: name => pages[name] ?? null,
    pageById: id => pagesById.get(id) ?? null,
    findChild: (page, name) => page.fields?.[name] ?? null,
    findChildren: () => [],
    clickButton: button => buttonClicks.push(button),
  },
});
runInContext(source('Installer.qs'), context, {filename: 'Installer.qs'});
runInContext(source('assistantscript.qs'), context, {filename: 'assistantscript.qs'});
const wizard = runInContext('new Controller()', context);
runInContext('new Component()', context);
assert.deepEqual(embedded.splice(0), [['ProgressForm', 'progress'], ['DoneForm', 'done'], ['AssistantForm', 'directory']],
  'The progress, launch and choice forms belong to Installing, Done and Install');
assert.equal(pages.PerformInstallationPage.title, '', 'Installing starts without a default page header');
assert.equal(metadata.get('directoryNext'), 'Install', 'The folder page offers the Install action');
assert.equal(visibility.get('components'), false, 'The default component tree is never a wizard stop');
assert.equal(visibility.get('start-menu'), false, 'The Start menu page is absent');
wizard.IntroductionPageCallback();
assert.deepEqual(buttonClicks.splice(0), ['Next'], 'Introduction passes without a visible choice');
wizard.TargetDirectoryPageCallback();
assert.deepEqual(buttonClicks, [], 'Install waits for the user on the first stop');
assert.equal(fields.AssistantCheckBox.checked, true, 'ChatGPT starts selected');
assert.equal(fields.AssistantCheckBox.text, 'ChatGPT', 'The first assistant row is ChatGPT');
assert.equal(fields.CopilotCheckBox.checked, false, 'GitHub Copilot starts unselected');
assert.equal(fields.CopilotCheckBox.text, 'GitHub Copilot', 'The Copilot row names it');
assert.equal(fields.CopilotBox.visible, true, 'A carried assistant has its row');
assert.equal(fields.ClaudeBox.visible, carriesClaude, 'The Claude row follows component availability');
if (carriesClaude) {
  assert.equal(fields.ClaudeCheckBox.checked, false, 'Claude starts unselected');
  assert.equal(fields.ClaudeCheckBox.text, 'Claude', 'The Claude row names it');
  assert.equal(fields.ClaudeSizeLabel.text, '40.00 MB', 'Claude has its own size');
}
assert.equal(fields.CopilotSizeLabel.text, '60.00 MB', 'Each assistant row shows its own size');
assert.match(fields.SpaceLabel.text, /^151\.00 MB needed/, 'Install space counts only the ticked assistants');
assert.match(fields.LicenseLink.text, /https:\/\/www\.gnu\.org\/licenses\/gpl-3\.0\.html/, 'The checkbox has a link to the GPL');

fields.LicenseCheckBox.checked = false;
wizard.ReadyForInstallationPageCallback();
assert.deepEqual(buttonClicks.splice(0), ['Back'], 'An unchecked license returns to Install without committing');
assert.equal(fields.NoticeBox.visible, true, 'The refusal displays its explanation on the Install page');
assert.match(fields.NoticeLabel.text, /accept.*license/i, 'The refusal names the unmet license choice');

fields.AssistantCheckBox.checked = false;
fields.AssistantCheckBox.toggled.emit(false);
assert.match(fields.SpaceLabel.text, /^123\.50 MB needed/, 'Unticking the assistant removes its bytes');
pages.TargetDirectoryPage.left.emit();
assert.deepEqual([...selected], [appName], 'Unticking excludes the assistant from the actual component request');
fields.LicenseCheckBox.checked = true;
wizard.ReadyForInstallationPageCallback();
assert.deepEqual(buttonClicks.splice(0), ['Commit'], 'An accepted license permits commit');
assert.match(summary.RemoveAllMsgLabel.text, /EasyDiffraction<\/td><td[^>]*>123\.50 MB/, 'The summary lists the base size');
assert.doesNotMatch(summary.RemoveAllMsgLabel.text, /ChatGPT|Claude|Copilot/, 'The summary omits the unchecked assistants');
assert.equal(summary.InstallComponentsWidget.visible, false, 'The install component tree is hidden from the summary');
assert.equal(summary.UninstallComponentsWidget.visible, false, 'The uninstall component tree is hidden from the summary');

fields.AssistantCheckBox.checked = true;
fields.AssistantCheckBox.toggled.emit(true);
pages.TargetDirectoryPage.left.emit();
wizard.ReadyForInstallationPageCallback();
assert.deepEqual([...selected], [appName, assistantName], 'Ticking selects the assistant at commit');
assert.match(summary.RemoveAllMsgLabel.text, /ChatGPT<\/td><td[^>]*>27\.50 MB/, 'The summary lists the selected assistant size');

assert.deepEqual(buttonClicks.splice(0), ['Commit'], 'The summary advances directly to Installing');

fields.CopilotCheckBox.checked = true;
fields.CopilotCheckBox.toggled.emit(true);
assert.match(fields.SpaceLabel.text, /^211\.00 MB needed/, 'Ticking Copilot adds its bytes');
pages.TargetDirectoryPage.left.emit();
wizard.ReadyForInstallationPageCallback();
buttonClicks.splice(0);
assert.deepEqual([...selected], [appName, assistantName, copilotName], 'Each ticked assistant is requested');
assert.match(summary.RemoveAllMsgLabel.text, /ChatGPT<\/td>.*GitHub Copilot<\/td><td[^>]*>60\.00 MB/,
  'The summary lists the assistants in the rows\' order');
assert.ok(!selected.has(claudeName), 'An unchecked or absent Claude component is never requested');

if (carriesClaude) {
  fields.ClaudeCheckBox.checked = true;
  fields.ClaudeCheckBox.toggled.emit(true);
  assert.match(fields.SpaceLabel.text, /^251\.00 MB needed/, 'Every selected assistant adds its own bytes');
  pages.TargetDirectoryPage.left.emit();
  wizard.ReadyForInstallationPageCallback();
  buttonClicks.splice(0);
  assert.deepEqual([...selected].sort(), [appName, assistantName, claudeName, copilotName].sort(),
    'All three assistants can be installed together');
  assert.match(summary.RemoveAllMsgLabel.text, /ChatGPT<\/td>.*Claude<\/td><td[^>]*>40\.00 MB.*GitHub Copilot<\/td>/,
    'The summary lists all selected providers in page order');
}

wizard.PerformInstallationPageCallback();
wizard.FinishedPageCallback();
assert.deepEqual(buttonClicks, [], 'The progress and Done pages add no intermediate choice or component tree');

for (mode of ['maintenance', 'update', 'remove', 'cli']) {
  const controller = mode === 'cli' ? null : runInContext('new Controller()', context);
  runInContext('new Component()', context);
  assert.deepEqual(embedded.splice(0), mode === 'cli' ? [] : [['ProgressForm', 'progress'], ['DoneForm', 'done']],
    'Graphical modes embed the progress and launch forms on Installing and Done');
  const hasAssistantChoice = mode === 'maintenance';
  assert.deepEqual(extraPages.splice(0), hasAssistantChoice ? [['AssistantForm', 'ready']] : [],
    'Change components offers an assistant choice; Update goes directly to its summary');
  if (controller) {
    controller.IntroductionPageCallback();
    if (hasAssistantChoice)
      controller.DynamicAssistantFormCallback();
    controller.ReadyForInstallationPageCallback();
    controller.PerformInstallationPageCallback();
    controller.FinishedPageCallback();
  }
}
