const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function main() {
  const [asset, change, outcome, dialogApi = 'native', repeat = 'once'] = process.argv.slice(2);
  const initial = {
    reason: 'Report a problem', message: 'Submitted message A', subject: 'Submitted subject A',
    name: 'Person A', email: 'a@example.invalid', affiliation: 'Institute A',
  };
  const later = {
    reason: 'Suggest an idea', message: 'Later message B\nwith a correction', subject: 'Later subject B',
    name: 'Person B', email: 'b@example.invalid', affiliation: 'Institute B',
  };
  const defaults = {...Object.fromEntries(Object.keys(initial).map(name => [name, ''])), reason: 'Share feedback'};
  const document = {readyState: 'complete', activeElement: null, modal: null};
  function element(tag) {
    const data = Object.create(null);
    const node = {
      tagName: tag.toUpperCase(), children: [], parentNode: null, dataset: {}, attributes: {},
      listeners: {}, textContent: '', className: '', disabled: false,
      addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
      setAttribute(name, value) {
        this.attributes[name] = String(value);
        if (name === 'open') this.open = true;
        if (name.startsWith('data-')) data[name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = String(value);
      },
      getAttribute(name) { return this.attributes[name] ?? null; },
      append(...nodes) { for (const child of nodes) insert(this, child, this.children.length); },
      after(...nodes) {
        if (!this.parentNode) return;
        let position = this.parentNode.children.indexOf(this) + 1;
        for (const child of nodes) insert(this.parentNode, child, position++);
      },
      dispatchEvent(event) {
        event.target ||= this;
        event.currentTarget = this;
        event.preventDefault ||= function() { this.defaultPrevented = true; };
        for (const handler of [...(this.listeners[event.type] || [])]) handler.call(this, event);
        if (event.bubbles && !event.cancelBubble && this.parentNode) this.parentNode.dispatchEvent(event);
        return !event.defaultPrevented;
      },
      focus() { if (!this.disabled) document.activeElement = this; },
      click() { if (!this.disabled) { this.focus(); this.dispatchEvent({type: 'click'}); } },
      querySelector(selector) { return this.querySelectorAll(selector)[0] || null; },
      querySelectorAll(selector) {
        return descendants(this).filter(child => {
          if (selector.startsWith('.')) return child.className.split(/\s+/).includes(selector.slice(1));
          if (selector === 'button[type="submit"]') return child.tagName === 'BUTTON' && child.type === 'submit';
          throw new Error('The DOM fixture must explicitly support a new selector: ' + selector);
        });
      },
    };
    node.dataset = new Proxy(data, {set(target, key, value) {
      target[key] = String(value);
      node.attributes['data-' + key.replace(/[A-Z]/g, letter => '-' + letter.toLowerCase())] = String(value);
      return true;
    }});
    if (tag === 'dialog') {
      node.open = false;
      node.modal = false;
      node.opens = 0;
      node.closes = 0;
      node.showModal = function() {
        if (this.open && !this.modal) throw new Error('A nonmodal dialog is already open');
        if (this.open) return;
        this.previousFocus = document.activeElement;
        this.open = this.modal = true;
        this.setAttribute('open', '');
        document.modal = this;
        ++this.opens;
        const first = descendants(this).find(child => child.tagName === 'BUTTON' && !child.disabled);
        if (first) first.focus();
      };
      node.close = function() {
        if (!this.open) return;
        this.open = this.modal = false;
        delete this.attributes.open;
        if (document.modal === this) document.modal = null;
        ++this.closes;
        if (descendants(this).includes(document.activeElement))
          document.activeElement = this.previousFocus && !this.previousFocus.disabled ? this.previousFocus : document.body;
        this.dispatchEvent({type: 'close'});
      };
      if (dialogApi === 'fallback') node.showModal = undefined;
    }
    return node;
  }
  function insert(parent, child, position) {
    if (child.parentNode) {
      const old = child.parentNode.children.indexOf(child);
      child.parentNode.children.splice(old, 1);
    }
    child.parentNode = parent;
    parent.children.splice(position, 0, child);
  }
  function descendants(root) { return root.children.flatMap(child => [child, ...descendants(child)]); }
  const page = document.body = element('body');
  document.activeElement = page;
  const form = element('form');
  form.className = 'ed-contact-form';
  page.append(form);
  const elements = Object.fromEntries(Object.entries(initial).map(([name, value]) => {
    const field = element(name === 'reason' ? 'select' : name === 'message' ? 'textarea' : 'input');
    Object.assign(field, {name, value, type: 'text'});
    form.append(field);
    return [name, field];
  }));
  elements.reason.options = [];
  elements.reason.add = function(option) { this.options.push(option); if (this.options.length === 1) this.value = option.value; };
  const note = element('p');
  note.className = 'ed-contact-note';
  const button = element('button');
  button.type = 'submit';
  form.append(note, button);
  const controls = Object.assign([...Object.values(elements), button], elements);
  controls.namedItem = name => elements[name];
  form.elements = controls;
  form.resets = 0;
  form.reset = function() {
    ++this.resets;
    for (const [name, value] of Object.entries(defaults)) elements[name].value = value;
    this.dispatchEvent({type: 'reset'});
  };
  const subscribers = [];
  document.querySelectorAll = selector => {
    assert.equal(selector, 'form.ed-contact-form', 'ADR-0063: setup discovers the actual contact form');
    return page.children.filter(child => child.tagName === 'FORM' && child.className === 'ed-contact-form');
  };
  document.createElement = element;
  let resolve, reject, sent, requests = 0, acceptedEdit = false;
  const endpoint = outcome === 'no-address' ? '' : 'https://feedback.example.invalid/feedback';
  const reasons = [
    {value: 'feedback', text: 'Share feedback'}, {value: 'question', text: 'Ask a question'},
    {value: 'problem', text: 'Report a problem'}, {value: 'idea', text: 'Suggest an idea'},
  ];
  const context = {
    window: {
      edFeedbackEndpoint: endpoint,
      edFeedbackForm: {
        endpoint, reasons, contact: {}, subject: {}, message: {}, privacy: '',
        status: {
          sending: 'Sending... [configured]',
          sent: 'Your message was sent. Thank you! [configured]',
          tooMany: 'Too many messages were sent from here recently. Please try again later. [configured]',
          offline: 'No connection to the feedback service. Check your connection and try again. [configured]',
          failed: 'Sending failed (%1). Please try again later. [configured]',
        },
        close: 'Close [configured]',
      },
      location: {pathname: '/about/community/'},
    },
    Option: function(text, value) { this.text = this.textContent = text; this.value = value; },
    setTimeout,
    document,
    document$: {subscribe(handler) { subscribers.push(handler); handler(); }},
    fetch(url, request) {
      ++requests;
      assert.equal(url, 'https://feedback.example.invalid/feedback');
      sent = JSON.parse(request.body);
      return new Promise((done, refused) => { resolve = done; reject = refused; });
    },
  };
  vm.runInNewContext(fs.readFileSync(asset, 'utf8'), context, {filename: asset});
  if (!elements.reason.options.length)
    for (const {text} of reasons) elements.reason.add({text, value: text});
  initial.reason = elements.reason.options.find(option => option.text === 'Report a problem').value;
  later.reason = elements.reason.options.find(option => option.text === 'Suggest an idea').value;
  defaults.reason = elements.reason.options[0].value;
  for (const [name, value] of Object.entries(initial)) elements[name].value = value;
  for (const setup of subscribers) setup();
  assert.equal(form.dataset.ready, 'true', 'ADR-0063: dataset readiness survives repeated setup');
  assert.equal(form.listeners.submit.length, 1, 'ADR-0063: navigation setup retains one actual submit handler');
  const status = form.querySelector('.ed-contact-status');
  assert.ok(status && status.parentNode === form, 'ADR-0063: the request status is inserted inside its real form');
  assert.equal(form.children.indexOf(status), form.children.indexOf(button) + 1, 'ADR-0063: status insertion follows the submit control');
  const submit = () => form.listeners.submit[0]({preventDefault() {}});
  button.focus();
  const pending = submit();
  if (outcome === 'no-address') {
    await pending;
    assert.equal(requests, 0, 'ADR-0063: a missing address never dispatches a request');
  } else {
    assert.equal(requests, 1, 'ADR-0063: one submit sends one immutable request');
    assert.equal(button.disabled, true, 'ADR-0063: duplicate Send is disabled while the request is pending');
    assert.deepEqual(sent, {
      kind: 'problem', text: initial.message, subject: initial.subject,
      contact: {name: initial.name, email: initial.email, affiliation: initial.affiliation},
      app: {source: 'website', page: '/about/community/'},
    }, 'ADR-0063: the transmitted request contains the submitted draft, not later edits');
    assert.equal(status.textContent, 'Sending... [configured]', 'ADR-0063: pending status uses the supplied status configuration');
    assert.equal(page.children.filter(child => child.tagName === 'DIALOG' && child.open).length, 0, 'ADR-0063: no confirmation precedes the held response');
    await submit();
    assert.equal(requests, 1, 'ADR-0063: a second submit cannot bypass the pending request guard');
    if (change !== 'none' && !elements[change].disabled) {
      elements[change].value = later[change];
      elements[change].dispatchEvent({type: 'input', bubbles: true, target: elements[change]});
      elements[change].dispatchEvent({type: 'change', bubbles: true, target: elements[change]});
      acceptedEdit = true;
    }
    if (outcome === 'network-error') reject(new TypeError('Independent offline fetch rejection'));
    else resolve({status: Number(outcome)});
    await pending;
  }
  for (const name of Object.keys(initial)) {
    const expected = acceptedEdit && change === name ? later[name] : initial[name];
    if (outcome === '201' && !acceptedEdit)
      assert.equal(elements[name].value, defaults[name], 'ADR-0063: ordinary success retains the website reset behavior');
    else if (outcome === '201' && acceptedEdit && name !== change)
      assert.ok([initial[name], defaults[name]].includes(elements[name].value), 'ADR-0063: only an unchanged submitted field may be retained or reset');
    else
      assert.equal(elements[name].value, expected, 'ADR-0063 F1: success may not clear an unsubmitted draft; failure and no-address preserve fields: ' + name);
  }
  assert.equal(button.disabled, false, 'ADR-0063: completion or refusal releases Send');
  assert.equal(sent === undefined || sent.text === initial.message, true, 'ADR-0063: completion never rewrites the transmitted payload snapshot');
  if (outcome === '429') assert.match(status.textContent, /Too many messages/, 'ADR-0063: rate limiting keeps its existing explanation');
  if (outcome === '0') assert.match(status.textContent, /No connection/, 'ADR-0063: offline submission keeps its existing explanation');
  if (outcome === '400') assert.match(status.textContent, /Sending failed \(400\)/, 'ADR-0063: ordinary failure keeps its status-specific explanation');
  if (outcome === 'no-address') assert.match(status.textContent, /not available/, 'ADR-0063: missing-address feedback remains visible');
  assert.equal(form.resets, outcome === '201' ? 1 : 0, 'ADR-0063: only a successful response resets the submitted form');
  const notices = page.children.filter(child => child.tagName === 'DIALOG');
  assert.equal(notices.length, 1, 'ADR-0063: repeated setup inserts one real confirmation dialog after the form');
  const notice = notices[0];
  assert.equal(page.children.indexOf(notice), page.children.indexOf(form) + 1, 'ADR-0063: the confirmation is a sibling inserted after its form');
  assert.ok(notice.className.split(/\s+/).includes('ed-contact-notice'), 'ADR-0063: the modal uses the theme-aware notice presentation');
  const paragraphs = notice.children.filter(child => child.tagName === 'P');
  const closeButtons = notice.children.filter(child => child.tagName === 'BUTTON');
  assert.equal(paragraphs.length, 1, 'ADR-0063: the confirmation appends its visible message');
  assert.equal(closeButtons.length, 1, 'ADR-0063: the confirmation appends one usable Close button');
  const close = closeButtons[0];
  assert.equal(close.textContent, 'Close [configured]', 'ADR-0063: the dialog Close label uses the supplied configuration');
  assert.equal(close.type, 'button', 'ADR-0063: closing the notice never submits the form');
  assert.equal(close.listeners.click.length, 1, 'ADR-0063: Close retains one actual dismissal handler');
  const words = {
    '201': 'Your message was sent. Thank you! [configured]',
    '429': 'Too many messages were sent from here recently. Please try again later. [configured]',
    '0': 'No connection to the feedback service. Check your connection and try again. [configured]',
    'network-error': 'No connection to the feedback service. Check your connection and try again. [configured]',
    '400': 'Sending failed (400). Please try again later. [configured]',
  };
  function confirmation(expectedWords, sentSuccessfully) {
    assert.equal(notice.open, true, 'ADR-0063: a completed request opens a confirmation over the page');
    assert.notEqual(notice.getAttribute('open'), null, 'ADR-0063: dialog open state is represented in the DOM');
    assert.equal(notice.modal, dialogApi === 'native', 'ADR-0063: showModal enters modal state and the open-attribute fallback stays nonmodal');
    assert.equal(document.modal === notice, dialogApi === 'native', 'ADR-0063: native confirmation belongs to the modal document layer');
    assert.equal(paragraphs[0].textContent, expectedWords, 'ADR-0063: the visible confirmation uses the independent status-specific configured answer');
    assert.equal(status.textContent, expectedWords, 'ADR-0063: inline and prominent confirmation agree for the sent request');
    assert.equal(notice.dataset.outcome, sentSuccessfully ? 'sent' : 'failed', 'ADR-0063: the confirmation selects its success or failure presentation');
    assert.equal(notice.getAttribute('data-outcome'), sentSuccessfully ? 'sent' : 'failed', 'ADR-0063: dataset updates reach the attribute consumed by notice styling');
    assert.equal(notice.getAttribute('role'), sentSuccessfully ? 'status' : 'alert', 'ADR-0063: failure confirmation is announced as an alert');
    assert.equal(document.activeElement, close, 'ADR-0063: the opened confirmation focuses its usable Close button');
    const draft = Object.fromEntries(Object.entries(elements).map(([name, field]) => [name, field.value]));
    close.click();
    assert.equal(notice.open, false, 'ADR-0063: clicking the actual Close handler dismisses the confirmation');
    assert.equal(notice.getAttribute('open'), null, 'ADR-0063: dismissal clears the DOM open state');
    assert.equal(document.modal, null, 'ADR-0063: dismissal releases the modal document layer');
    assert.ok(!descendants(notice).includes(document.activeElement), 'ADR-0063: focus does not remain inside the dismissed confirmation');
    assert.deepEqual(Object.fromEntries(Object.entries(elements).map(([name, field]) => [name, field.value])), draft, 'ADR-0063: dismissing confirmation never clears or changes the current form');
  }
  if (outcome === 'no-address') {
    assert.equal(notice.open, false, 'ADR-0063: a missing address keeps its inline explanation without a delivery confirmation');
    assert.equal(notice.opens, 0, 'ADR-0063: no-address refusal never opens a modal');
    assert.equal(notice.closes, 0, 'ADR-0063: no-address refusal needs no modal dismissal');
  } else {
    confirmation(words[outcome], outcome === '201');
    assert.equal(notice.closes, 1, 'ADR-0063: the first actual confirmation is dismissed once');
  }
  if (repeat === 'repeat') {
    for (const setup of subscribers) setup();
    assert.equal(page.children.filter(child => child.tagName === 'DIALOG').length, 1, 'ADR-0063: navigation and resubmission reuse the existing dialog');
    for (const [name, value] of Object.entries(later)) elements[name].value = value;
    const next = submit();
    assert.equal(requests, 2, 'ADR-0063: a dismissed confirmation leaves the form able to send a successor');
    assert.equal(sent.text, later.message, 'ADR-0063: the next request contains its own independent draft');
    resolve({status: 429});
    await next;
    confirmation(words['429'], false);
    assert.equal(elements.message.value, later.message, 'ADR-0063: the successor failure retains its retry text after dismissal');
    assert.equal(form.resets, 1, 'ADR-0063: only the earlier successful request reset the form');
    assert.equal(notice.closes, 2, 'ADR-0063: the same confirmation opens and closes for both results');
    assert.equal(button.disabled, false, 'ADR-0063: confirmation reuse leaves Send unlocked');
  }
  console.log(JSON.stringify({change, outcome, dialogApi, repeat, acceptedEdit, requests, passed: true}));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
