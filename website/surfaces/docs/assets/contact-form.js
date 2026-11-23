// SPDX-License-Identifier: BSD-3-Clause
/* Send the Get in touch form to the feedback service the app uses (ADR-0063), as the app's form would. Its address and
   wording come from the app at site build (assets/feedback-form.js), so the form says what the app's form says. */
(() => {
  const app = window.edFeedbackForm || null;
  // The app's limit on the text.
  const maxTextCharacters = 20000;

  const rules = window.edFeedbackPayload || null;
  const PAPERCLIP = '<svg viewBox="0 0 448 512" aria-hidden="true" focusable="false"><path d="M43.246 466.142c-58.43-60.289-57.341-157.511 1.386-217.581L254.392 34c44.316-45.332 116.351-45.336 160.671 0 43.89 44.894 43.943 117.329 0 162.276L232.214 383.128c-29.855 30.537-78.633 30.111-107.982-.998-28.275-29.97-27.368-77.473 1.452-106.953l143.743-146.835c6.182-6.314 16.312-6.422 22.626-.241l22.861 22.379c6.315 6.182 6.422 16.312.241 22.626L171.427 319.927c-4.932 5.045-5.236 13.428-.648 18.292 4.372 4.634 11.245 4.711 15.688.165l182.849-186.851c19.613-20.062 19.613-52.725-.011-72.798-19.189-19.627-49.957-19.637-69.154 0L90.39 293.295c-34.763 35.56-35.299 93.12-1.191 128.313 34.01 35.093 88.985 35.137 123.058.286l172.06-175.999c6.177-6.319 16.307-6.433 22.626-.256l22.877 22.364c6.319 6.177 6.432 16.307.256 22.626l-172.06 175.998c-59.576 60.938-155.943 60.216-214.77-.485z"/></svg>';

  // What the form sends: the message (one kind, feedback, as the app sends it), the contact fields that are filled in,
  // where on the website it was sent from, and the attached files as the app sends them. Nothing else.
  function payload(form, files) {
    const value = name => (form.elements[name] ? form.elements[name].value.trim() : '');
    const message = { kind: 'feedback', text: value('message').slice(0, maxTextCharacters) };
    const contact = {};
    for (const key of ['name', 'email', 'affiliation']) if (value(key)) contact[key] = value(key);
    if (Object.keys(contact).length) message.contact = contact;
    message.app = { source: 'website', page: window.location.pathname };
    if (files && files.length) message.attachments = files.map(({ name, type, size, data }) => ({ name, type, size, data }));
    return message;
  }

  // A file the browser read, as the app's form holds one: name, type, size and base64 data.
  function readFile(file) {
    // A file past the limit for one file keeps its size, which the form refuses, and is never read.
    if (rules && file.size > rules.maxFileBytes) return Promise.resolve({ name: file.name, type: file.type, size: file.size, data: '' });
    return new Promise(resolve => {
      const reader = new FileReader();
      reader.onload = () => resolve({ name: file.name, type: file.type, size: file.size, data: String(reader.result).split(',')[1] || '' });
      reader.onerror = () => resolve({ name: file.name, unreadable: true });
      reader.readAsDataURL(file);
    });
  }

  function sizeText(bytes) {
    return bytes < 1000 ? `${bytes} B` : bytes < 1000000 ? `${(bytes / 1000).toFixed(1)} KB` : `${(bytes / 1000000).toFixed(1)} MB`;
  }

  // The service's answer in the app's words: with `detail`, what the service said (or which files it did not keep).
  function answer(status, detail = '') {
    const words = app.status;
    if (status === 201) return detail ? `${words.sent} ${words.but.replace('%1', detail)}` : words.sent;
    if (status === 429) return words.tooMany;
    if (status === 0) return detail ? words.notSent.replace('%1', detail) : words.offline;
    if (detail) return words.refused.replace('%1', String(status)).replace('%2', detail);
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

  // The app's field prompts: the contact fields' and the message's, which asks what the message is about.
  function fill(form) {
    if (!app) return;
    for (const key of ['name', 'email', 'affiliation']) {
      const field = form.elements[key];
      if (field) field.placeholder = field.ariaLabel = app.contact[key];
    }
    if (form.elements.message) form.elements.message.placeholder = form.elements.message.ariaLabel = app.message;
  }

  // Attach files: the link under the message (its tooltip the app's), the browser's picker, a drop on the form, the
  // list with Remove, and the app's limits, a refused limit keeping Send off. Returns the files as the form holds them.
  function attachments(form) {
    const files = [];
    const box = form.querySelector('.ed-contact-files');
    if (!box || !app || !app.files || !rules) return files;
    const link = box.querySelector('.ed-contact-attach');
    const picker = box.querySelector('input[type="file"]');
    const list = box.querySelector('.ed-contact-file-list');
    const error = box.querySelector('.ed-contact-file-error');
    const send = form.querySelector('button[type="submit"]');
    link.innerHTML = PAPERCLIP;
    link.append(app.files.attach);
    link.title = app.files.tooltip;
    link.setAttribute('aria-label', `${app.files.attach}. ${app.files.tooltip}`);
    const render = unreadable => {
      list.replaceChildren(...files.map((file, index) => {
        const item = document.createElement('li');
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'ed-contact-remove';
        remove.textContent = app.files.remove;
        remove.addEventListener('click', () => {
          files.splice(index, 1);
          render([]);
        });
        item.append(`${file.name} · ${sizeText(file.size)}`, remove);
        return item;
      }));
      const problem = rules.filesProblem(files);
      error.textContent = problem ? app.files.refused.replace('%1', problem)
        : unreadable && unreadable.length ? app.files.unreadable.replace('%1', unreadable.join(', ')) : '';
      send.disabled = Boolean(problem);
    };
    const add = async chosen => {
      const read = await Promise.all(Array.from(chosen || []).map(readFile));
      files.push(...read.filter(file => !file.unreadable));
      render(read.filter(file => file.unreadable).map(file => file.name));
    };
    link.addEventListener('click', () => picker.click());
    picker.addEventListener('change', () => {
      add(picker.files);
      picker.value = '';
    });
    // A file dropped anywhere on the form is attached; the form shows where it goes while one is dragged over it.
    const dragging = event => event.dataTransfer && Array.from(event.dataTransfer.types || []).includes('Files');
    form.addEventListener('dragover', event => {
      if (!dragging(event)) return;
      event.preventDefault();
      form.classList.add('ed-contact-dropping');
    });
    form.addEventListener('dragleave', event => {
      if (!form.contains(event.relatedTarget)) form.classList.remove('ed-contact-dropping');
    });
    form.addEventListener('drop', event => {
      if (!dragging(event)) return;
      event.preventDefault();
      form.classList.remove('ed-contact-dropping');
      add(event.dataTransfer.files);
    });
    files.render = render;
    return files;
  }

  function setup() {
    document.querySelectorAll('form.ed-contact-form').forEach(form => {
      if (form.dataset.ready) return;
      form.dataset.ready = 'true';
      fill(form);
      const files = attachments(form);
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
        const message = payload(form, files);
        const names = files.map(file => file.name);
        pending = true;
        controls.forEach(element => (element.disabled = true));
        status.textContent = app.status.sending;
        let code = 0;
        let text = '';
        try {
          const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(message),
          });
          code = response.status;
          text = await response.text();
        } catch {
          code = 0;
        }
        // What the service said, and for a 201 the files it did not confirm: a 201 is never a plain success then.
        let detail = '';
        try {
          const said = JSON.parse(text || '{}');
          detail = (code === 201 ? said.warning : said.error) || '';
        } catch {
          detail = '';
        }
        const missing = code === 201 && rules ? rules.unconfirmedFiles(names, text) : [];
        if (missing.length) detail = (missing.length === 1 ? app.files.notAttached : app.files.notAttachedMany).replace('%1', missing.join(', '));
        // The answer is the one to this request: the fields stayed as sent while it was pending.
        // The answer shows only in the notice, so the line under Send is cleared rather than repeating it.
        const words = answer(code, detail);
        status.textContent = '';
        if (code === 201) {
          // Only the message is cleared: the contact details stay for the next one.
          if (form.elements.message) form.elements.message.value = '';
          files.splice(0, files.length);
          if (files.render) files.render([]);
        }
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
