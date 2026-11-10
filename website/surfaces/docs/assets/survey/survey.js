// SPDX-License-Identifier: BSD-3-Clause
/* The survey on About → Survey. The questions are listed here once; the form is built from them. The events come from
   events.json beside this file: "General" always, any other only between its start and end dates. Answers go to the
   feedback service the Get in touch form uses, at its /survey address. */
(() => {
  const app = window.edFeedbackForm || null;
  // Read while the script runs: events.json sits beside it.
  const eventsUrl = new URL('events.json', document.currentScript ? document.currentScript.src : window.location.href).href;
  const scale = (low, high) => Array.from({ length: high - low + 1 }, (_, i) => String(low + i));
  const interfaces = [
    ['web', 'Web application'],
    ['desktop', 'Desktop application'],
    ['notebooks', 'Python library in Jupyter notebooks'],
    ['scripting', 'Python library in scripts'],
    ['cli', 'Standalone command-line tool'],
    ['cli_python', 'Command-line tool as a Python package (without Python scripting)'],
  ];

  // Each question: its key in the answers, its kind, its wording and its choices. A choice list starting with "none"
  // makes "none" exclusive.
  const sections = [
    {
      title: 'About you',
      questions: [
        { key: 'position', kind: 'one', text: 'Your position', choices: ['Student', 'PhD student', 'Postdoc', 'Staff scientist', 'Instrument scientist', 'Professor or group leader', 'Industry', 'Other'] },
        { key: 'field', kind: 'one', text: 'Your field', choices: ['Physics', 'Chemistry', 'Materials science', 'Earth sciences', 'Biology', 'Engineering', 'Other'] },
        { key: 'experience', kind: 'one', text: 'Your experience with diffraction data analysis', choices: ['None yet', 'Less than a year', '1 to 3 years', '3 to 10 years', 'More than 10 years'] },
        { key: 'tools', kind: 'many', text: 'Programs you use now', choices: ['None', 'FullProf', 'GSAS-II', 'TOPAS', 'JANA', 'Other'] },
      ],
    },
    {
      title: 'Ways to use EasyDiffraction',
      note: 'For each way of working: how interested you are (1 not at all, 5 very), whether you have tried it, and if so how easy it was (1 hard, 5 easy).',
      questions: [{ key: 'interfaces', kind: 'interfaces', rows: interfaces }],
    },
    {
      title: 'Your experience so far',
      questions: [
        { key: 'install', kind: 'scale', text: 'Installing and starting it (1 hard, 5 easy)', choices: scale(1, 5), skip: 'Not tried' },
        { key: 'docs', kind: 'scale', text: 'Documentation and tutorials (1 not helpful, 5 very helpful)', choices: scale(1, 5), skip: 'Not read' },
        { key: 'features', kind: 'scale', text: 'How well the features fit your work (1 poorly, 5 well)', choices: scale(1, 5), skip: 'Not sure' },
        { key: 'missing', kind: 'texts', count: 3, text: 'Up to three missing features you would need to use it' },
        { key: 'wishes', kind: 'texts', count: 3, text: 'Up to three features that would be nice to have' },
        { key: 'likely', kind: 'scale', text: 'How likely are you to use EasyDiffraction for your own work? (0 not at all, 10 certainly)', choices: scale(0, 10) },
      ],
    },
    {
      title: 'AI help',
      key: 'ai',
      questions: [
        { key: 'ai_interest', kind: 'scale', text: 'Your interest in AI help with diffraction analysis (1 low, 5 high)', choices: scale(1, 5), skip: 'Not interested', skipsSection: true },
        { key: 'ai_uses', kind: 'many', text: 'How you would like to use it', choices: ["The app's built-in assistant", 'My own assistant writing notebooks or projects', 'Converting projects from other programs (FullProf, GSAS-II, …)', 'Explaining fit results or suggesting a fit strategy', 'Other'] },
        { key: 'ai_providers', kind: 'many', text: 'Providers you use or could use', choices: ['None', 'ChatGPT (OpenAI)', 'Claude (Anthropic)', 'GitHub Copilot', 'Gemini (Google)', 'A local or self-hosted model', 'A service from my institution', 'Other'] },
        { key: 'ai_access', kind: 'one', text: 'How you would prefer to get access', choices: ['Sign in with my existing subscription', 'My own API key (pay per use)', 'Provided by my institution', 'Only if free', 'Not sure'] },
        { key: 'ai_data', kind: 'one', text: 'Sending your data to an AI provider is', choices: ['Fine', 'Fine without the measured data', 'Not allowed for my work', 'Not sure'] },
        { key: 'ai_assistant', kind: 'scale', text: "The app's built-in assistant, if you tried it (1 poor, 5 very good)", choices: scale(1, 5), skip: "Didn't try" },
        { key: 'ai_assistant_note', kind: 'text', text: 'What worked or did not' },
      ],
    },
    {
      title: 'Anything else',
      questions: [
        { key: 'comments', kind: 'area', text: 'Anything else you would like to tell us' },
        { key: 'email', kind: 'email', text: 'Your e-mail, if we may contact you about your answers' },
      ],
    },
  ];

  const element = (tag, attributes = {}, children = []) => {
    const node = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) {
      if (name === 'text') node.textContent = value;
      else node.setAttribute(name, value);
    }
    node.append(...children);
    return node;
  };
  const slug = text => text.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');

  // A row of radio buttons, with an optional "skip" choice at its end.
  function choiceRow(name, choices, skip) {
    const row = element('div', { class: 'ed-survey-choices' });
    for (const choice of skip ? [...choices, skip] : choices) {
      row.append(element('label', {}, [element('input', { type: 'radio', name, value: choice === skip ? 'skip' : choice }), choice]));
    }
    return row;
  }

  function question(q) {
    const box = element('fieldset', { class: 'ed-survey-question', 'data-key': q.key });
    if (q.text) box.append(element('legend', { text: q.text }));
    if (q.kind === 'one' || q.kind === 'scale') box.append(choiceRow(q.key, q.choices, q.skip));
    if (q.kind === 'many') {
      const row = element('div', { class: 'ed-survey-choices' });
      for (const choice of q.choices) row.append(element('label', {}, [element('input', { type: 'checkbox', name: q.key, value: choice }), choice]));
      // "None" first is exclusive: ticking it clears the others, ticking another clears it.
      if (q.choices[0] === 'None') {
        row.addEventListener('change', event => {
          const boxes = Array.from(row.querySelectorAll('input'));
          if (!event.target.checked) return;
          if (event.target.value === 'None') boxes.slice(1).forEach(other => (other.checked = false));
          else boxes[0].checked = false;
        });
      }
      box.append(row);
    }
    if (q.kind === 'texts') for (let i = 0; i < q.count; ++i) box.append(element('input', { type: 'text', name: q.key, 'aria-label': `${q.text} ${i + 1}`, maxlength: '300' }));
    if (q.kind === 'text') box.append(element('input', { type: 'text', name: q.key, 'aria-label': q.text, maxlength: '500' }));
    if (q.kind === 'area') box.append(element('textarea', { name: q.key, 'aria-label': q.text, maxlength: '5000' }));
    if (q.kind === 'email') {
      box.append(element('input', { type: 'email', name: q.key, 'aria-label': q.text }));
      box.append(element('label', { class: 'ed-survey-consent' }, [element('input', { type: 'checkbox', name: 'consent' }), 'You may contact me at this address about my answers.']));
    }
    if (q.kind === 'interfaces') {
      const table = element('table', { class: 'ed-survey-interfaces' });
      table.append(element('tr', {}, ['', 'Interest', 'Tried', 'Ease of use'].map(text => element('th', { text }))));
      for (const [key, label] of q.rows) {
        table.append(element('tr', {}, [
          element('th', { text: label, scope: 'row' }),
          element('td', {}, [choiceRow(`interest_${key}`, scale(1, 5))]),
          element('td', {}, [element('input', { type: 'checkbox', name: `tried_${key}`, 'aria-label': `Tried: ${label}` })]),
          element('td', {}, [choiceRow(`ease_${key}`, scale(1, 5))]),
        ]));
      }
      box.append(table);
    }
    return box;
  }

  // The events open today, by the visitor's calendar date; "General" first.
  function activeEvents(events, today) {
    return events.filter(event => (!event.start || event.start <= today) && (!event.end || today <= event.end));
  }

  function answers(form) {
    const data = new FormData(form);
    const out = {};
    for (const section of sections) {
      for (const q of section.questions) {
        if (q.kind === 'interfaces') {
          for (const [key] of q.rows) {
            const row = { interest: data.get(`interest_${key}`), tried: data.get(`tried_${key}`) === 'on', ease: data.get(`ease_${key}`) };
            if (row.interest || row.tried || row.ease) out[`interface_${key}`] = row;
          }
        } else if (q.kind === 'many' || q.kind === 'texts') {
          const values = data.getAll(q.key).map(value => String(value).trim()).filter(Boolean);
          if (values.length) out[q.key] = values;
        } else if (q.kind !== 'email') {
          const value = String(data.get(q.key) || '').trim();
          if (value) out[q.key] = value;
        }
      }
    }
    // "Not interested" in AI help leaves the rest of that section out.
    if (out.ai_interest === 'skip') for (const q of sections.find(s => s.key === 'ai').questions.slice(1)) delete out[q.key];
    return out;
  }

  function build(form, events) {
    const event = element('fieldset', { class: 'ed-survey-question', 'data-key': 'event' }, [element('legend', { text: 'Event' })]);
    const select = element('select', { name: 'event', 'aria-label': 'Event' });
    for (const { name, title } of events) select.add(new Option(title, name));
    event.append(select);
    form.append(event);
    for (const section of sections) {
      const part = element('section', { class: 'ed-survey-section', id: `survey-${slug(section.title)}` }, [element('h2', { text: section.title })]);
      if (section.note) part.append(element('p', { text: section.note }));
      part.append(...section.questions.map(question));
      form.append(part);
    }
    // "Not interested" greys out the rest of the AI section.
    const ai = form.querySelector('#survey-ai_help');
    ai.addEventListener('change', () => {
      const off = form.elements.ai_interest.value === 'skip';
      ai.querySelectorAll('.ed-survey-question').forEach((box, index) => index > 0 && (box.disabled = off));
    });
    const send = element('button', { type: 'submit', text: 'Send' });
    const status = element('p', { class: 'ed-contact-status', role: 'status' });
    form.append(send, status);
    return status;
  }

  async function setup() {
    for (const form of document.querySelectorAll('form.ed-survey-form')) {
      if (form.dataset.ready) continue;
      form.dataset.ready = 'true';
      let events = [{ name: 'general', title: 'General' }];
      try {
        const response = await fetch(eventsUrl);
        if (response.ok) events = activeEvents((await response.json()).events, new Date().toISOString().slice(0, 10));
      } catch {
        // Offline or a copy without the file: General only.
      }
      const status = build(form, events);
      const endpoint = app ? app.endpoint.replace(/\/feedback$/, '/survey') : '';
      let pending = false;
      form.addEventListener('submit', async submit => {
        submit.preventDefault();
        if (pending) return;
        if (!endpoint) {
          status.textContent = 'Sending is not available on this copy of the site.';
          return;
        }
        const message = { event: form.elements.event.value || 'general', answers: answers(form), app: { source: 'website', page: window.location.pathname } };
        const email = form.elements.email.value.trim();
        if (email && form.elements.consent.checked) message.contact = { email };
        pending = true;
        status.textContent = app.status.sending;
        let code = 0;
        try {
          code = (await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(message) })).status;
        } catch {
          code = 0;
        }
        status.textContent = code === 201 ? 'Thank you! Your answers were sent.' : code === 429 ? app.status.tooMany : code === 0 ? app.status.offline : app.status.failed.replace('%1', String(code));
        if (code === 201) form.reset();
        pending = false;
      });
    }
  }

  window.edSurvey = { sections, activeEvents, answers };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
  else setup();
  if (typeof document$ !== 'undefined') document$.subscribe(setup);
})();
