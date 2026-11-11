// SPDX-License-Identifier: BSD-3-Clause
/* Send the Get in touch form to the feedback service the app uses (ADR-0063), as the app's form would. Its address and
   wording come from the app at site build (assets/feedback-form.js), so the form says what the app's form says. */
(() => {
  const app = window.edFeedbackForm || null;
  // The app's limit on the text.
  const maxTextCharacters = 20000;

  // What the form sends: the reason as the service's kind, the message, the subject and contact fields that are filled
  // in, and where on the website it was sent from. Nothing else.
  function payload(form) {
    const value = name => (form.elements[name] ? form.elements[name].value.trim() : '');
    const message = { kind: value('reason') || 'feedback', text: value('message').slice(0, maxTextCharacters) };
    if (value('subject')) message.subject = value('subject');
    const contact = {};
    for (const key of ['name', 'email', 'affiliation']) if (value(key)) contact[key] = value(key);
    if (Object.keys(contact).length) message.contact = contact;
    message.app = { source: 'website', page: window.location.pathname };
    return message;
  }

  // The service's answer in the app's words.
  function answer(status) {
    const words = app.status;
    if (status === 201) return words.sent;
    if (status === 429) return words.tooMany;
    if (status === 0) return words.offline;
    return words.failed.replace('%1', String(status));
  }

  // The answer to a sent message, in a window over the page as the app shows it, so it cannot be missed.
  function noticeFor(form) {
    const notice = document.createElement('dialog');
    notice.className = 'ed-contact-notice';
    const text = document.createElement('p');
    const close = document.createElement('button');
    close.type = 'button';
    close.textContent = app.close;
    close.addEventListener('click', () => notice.close());
    notice.append(text, close);
    form.after(notice);
    return (status, words) => {
      text.textContent = words;
      notice.dataset.outcome = status === 201 ? 'sent' : 'failed';
      notice.setAttribute('role', status === 201 ? 'status' : 'alert');
      if (typeof notice.showModal === 'function') notice.showModal();
      else notice.setAttribute('open', '');
      close.focus();
    };
  }

  // The same notice and words for the website's other form, the survey (assets/survey/survey.js).
  window.edNotice = { answer, noticeFor };

  // The app's reasons, field prompts and privacy line; the subject and message prompts follow the reason, as in the app.
  function fill(form) {
    if (!app) return;
    const reason = form.elements.reason;
    if (reason && !reason.options.length) {
      for (const { value, text } of app.reasons) reason.add(new Option(text, value));
    }
    for (const key of ['name', 'email', 'affiliation']) {
      const field = form.elements[key];
      if (field) field.placeholder = field.ariaLabel = app.contact[key];
    }
    const prompts = () => {
      const kind = reason ? reason.value : 'feedback';
      if (form.elements.subject) form.elements.subject.placeholder = form.elements.subject.ariaLabel = app.subject[kind] || '';
      if (form.elements.message) form.elements.message.placeholder = form.elements.message.ariaLabel = app.message[kind] || '';
    };
    prompts();
    if (reason) reason.addEventListener('change', prompts);
    form.addEventListener('reset', () => setTimeout(prompts));
    const note = form.querySelector('.ed-contact-note');
    if (note) note.textContent = app.privacy;
  }

  function setup() {
    document.querySelectorAll('form.ed-contact-form').forEach(form => {
      if (form.dataset.ready) return;
      form.dataset.ready = 'true';
      fill(form);
      const status = document.createElement('p');
      status.className = 'ed-contact-status';
      status.setAttribute('role', 'status');
      form.querySelector('button[type="submit"]').after(status);
      const endpoint = app ? app.endpoint : '';
      const show = app ? noticeFor(form) : null;
      let pending = false;
      form.addEventListener('submit', async event => {
        event.preventDefault();
        if (pending) return;
        if (!endpoint) {
          status.textContent = 'Sending is not available on this copy of the site.';
          return;
        }
        // The fields stay as sent until the answer arrives, so clearing them after a success never loses a later edit.
        const controls = Array.from(form.elements).filter(element => !element.disabled);
        const message = payload(form);
        pending = true;
        controls.forEach(element => (element.disabled = true));
        status.textContent = app.status.sending;
        let code = 0;
        try {
          const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(message),
          });
          code = response.status;
        } catch {
          code = 0;
        }
        // The answer is the one to this request: the fields stayed as sent while it was pending.
        // The answer shows only in the notice, so the line under Send is cleared rather than repeating it.
        const words = answer(code);
        status.textContent = '';
        if (code === 201) form.reset();
        show(code, words);
        controls.forEach(element => (element.disabled = false));
        pending = false;
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
  else setup();
  if (typeof document$ !== 'undefined') document$.subscribe(setup);
})();
