// SPDX-License-Identifier: BSD-3-Clause
// Exercise the shipped IFW script callbacks against an observable wizard port.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {createContext, runInContext} from 'node:vm';

const root = process.argv[2];
const source = name => readFileSync(join(root, name), 'utf8');
const ui = source('AssistantForm.ui');
for (const name of ['AssistantCheckBox', 'LicenseCheckBox'])
  assert.match(ui, new RegExp('<widget class="QCheckBox" name="' + name + '"'),
    'Both install choices are actual checkbox widgets');
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
const appName = 'org.easydiffraction.app';
const selected = new Set([appName]);
const fields = {
  AssistantCheckBox: {checked: false, toggled: signal()},
  LicenseCheckBox: {checked: false, toggled: signal()},
  LicenseLink: {},
  ShortcutCheckBox: {toggled: signal()},
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
  [assistantName, 'AI assistant', 27500000],
];
const components = records.map(([name, displayName, bytes]) => ({
  name,
  value(key) { return {DisplayName: displayName, UncompressedSize: String(bytes)}[key]; },
  installationRequested: () => selected.has(name),
  uninstallationRequested: () => false,
}));

const buttons = {
  NextButton: 'Next', BackButton: 'Back', CommitButton: 'Commit', FinishButton: 'Finish',
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
  component: {name: assistantName, userInterface: () => fields},
  installer: {
    status: 'success', isInstaller: () => mode === 'install',
    isUninstaller: () => mode === 'remove', isUpdater: () => mode === 'update',
    isPackageManager: () => mode === 'maintenance',
    isCommandLineInstance: () => mode === 'cli',
    setDefaultPageVisible(name, value) { visibility.set(name, value); },
    environmentVariable: () => '',
    fileExists: path => path === fields.TargetDirectoryLineEdit.text,
    execute(command) {
      assert.equal(command, '/bin/df', 'Only an available-space query is required');
      return ['Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 4000000 0 4000000 0% /', 0];
    },
    value: key => metadata.get(key) || '',
    setValue(key, value) { metadata.set(key, value); },
    components: () => components,
    selectComponent: name => selected.add(name),
    deselectComponent: name => selected.delete(name),
    addWizardPageItem: (_component, form, page) => embedded.push([form, page]),
    addWizardPage: (_component, form, page) => extraPages.push([form, page]),
    installationFinished: signal(), updateFinished: signal(), uninstallationFinished: signal(),
  },
  gui: {
    showSettingsButton() {},
    setWizardPageButtonText(page, button, text) { metadata.set(page + button, text); },
    pageWidgetByObjectName: name => pages[name],
    pageById: id => pagesById.get(id),
    findChild: (page, name) => page.fields[name],
    findChildren: () => [],
    clickButton: button => buttonClicks.push(button),
  },
});
runInContext(source('Installer.qs'), context, {filename: 'Installer.qs'});
runInContext(source('assistantscript.qs'), context, {filename: 'assistantscript.qs'});
const wizard = runInContext('new Controller()', context);
runInContext('new Component()', context);
assert.deepEqual(embedded.splice(0), [['ProgressForm', 'progress'], ['AssistantForm', 'directory']],
  'Progress belongs to Installing and the choices belong to Install');
assert.equal(pages.PerformInstallationPage.title, '', 'Installing starts without a default page header');
assert.equal(metadata.get('directoryNext'), 'Install', 'The folder page offers the Install action');
assert.equal(visibility.get('components'), false, 'The default component tree is never a wizard stop');
assert.equal(visibility.get('start-menu'), false, 'The Start menu page is absent');
wizard.IntroductionPageCallback();
assert.deepEqual(buttonClicks.splice(0), ['Next'], 'Introduction passes without a visible choice');
wizard.TargetDirectoryPageCallback();
assert.deepEqual(buttonClicks, [], 'Install waits for the user on the first stop');
assert.equal(fields.AssistantCheckBox.checked, true, 'The assistant starts selected');
assert.match(fields.SpaceLabel.text, /^151\.00 MB needed/, 'Install space includes both components');
assert.match(fields.LicenseLink.text, /https:\/\/www\.gnu\.org\/licenses\/gpl-3\.0\.html/, 'The checkbox has a link to the GPL');

fields.LicenseCheckBox.checked = false;
wizard.ReadyForInstallationPageCallback();
assert.deepEqual(buttonClicks.splice(0), ['Back'], 'An unchecked license returns to Install without committing');
assert.equal(fields.NoticeLabel.visible, true, 'The refusal displays its explanation on the Install page');
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
assert.doesNotMatch(summary.RemoveAllMsgLabel.text, /AI assistant/, 'The summary omits the unchecked assistant');
assert.equal(summary.InstallComponentsWidget.visible, false, 'The install component tree is hidden from the summary');
assert.equal(summary.UninstallComponentsWidget.visible, false, 'The uninstall component tree is hidden from the summary');

fields.AssistantCheckBox.checked = true;
fields.AssistantCheckBox.toggled.emit(true);
pages.TargetDirectoryPage.left.emit();
wizard.ReadyForInstallationPageCallback();
assert.deepEqual([...selected], [appName, assistantName], 'Ticking selects the assistant at commit');
assert.match(summary.RemoveAllMsgLabel.text, /AI assistant<\/td><td[^>]*>27\.50 MB/, 'The summary lists the selected assistant size');
assert.deepEqual(buttonClicks.splice(0), ['Commit'], 'The summary advances directly to Installing');
wizard.PerformInstallationPageCallback();
wizard.FinishedPageCallback();
assert.deepEqual(buttonClicks, [], 'The progress and Done pages add no intermediate choice or component tree');

for (mode of ['maintenance', 'update', 'remove', 'cli']) {
  runInContext('new Component()', context);
  assert.deepEqual(embedded.splice(0), mode === 'cli' ? [] : [['ProgressForm', 'progress']],
    'Every graphical mode embeds the progress form on its progress page');
  assert.deepEqual(extraPages.splice(0), mode === 'maintenance' ? [['AssistantForm', 'ready']] : [],
    'Maintenance alone gets a separate assistant choice');
}
