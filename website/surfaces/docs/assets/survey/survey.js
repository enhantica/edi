// SPDX-License-Identifier: BSD-3-Clause
/* The survey on About → Survey. The questions are listed here once; the form is built from them, with the field look
   of the Get in touch form. The events come from events.json beside this file: "General" always, any other only
   between its start and end dates. Answers go to the feedback service the Get in touch form uses, at /survey. */
(() => {
  const app = window.edFeedbackForm || null;
  // Read while the script runs: events.json sits beside it.
  const eventsUrl = new URL('events.json', document.currentScript ? document.currentScript.src : window.location.href).href;

  // A rating as select options, each named so it reads without the column header: the number, then its words; a
  // longer scale names only some points. The value stored is the number.
  const scale = (start, words) =>
    words.map((word, i) => ({ value: String(start + i), text: word ? `${start + i} ${word}` : String(start + i) }));
  const interest = scale(1, ['Not interested at all', 'Slightly interested', 'Moderately interested', 'Very interested', 'Extremely interested']);
  const ease = scale(1, ['Very hard', 'Hard', 'Neither hard nor easy', 'Easy', 'Very easy']);
  const helpful = scale(1, ['Not helpful at all', 'Slightly helpful', 'Moderately helpful', 'Very helpful', 'Extremely helpful']);
  const fit = scale(1, ['Fits very poorly', 'Fits poorly', 'Fits somewhat', 'Fits well', 'Fits very well']);
  const likely = scale(0, ['Not at all likely', '', '', '', '', 'Neither likely nor unlikely', '', '', '', '', 'Extremely likely']);
  const quality = scale(1, ['Very poor', 'Poor', 'Fair', 'Good', 'Very good']);
  const interfaces = [
    ['web', 'Web application'],
    ['desktop', 'Desktop application'],
    ['notebooks', 'Python library in Jupyter notebooks'],
    ['scripting', 'Python library in scripts'],
    ['cli', 'Standalone command-line tool'],
    ['cli_python', 'Command-line tool as a Python package'],
  ];

  // Each question: its key in the answers, its kind and wording. "one" and "rating" are selects; "many" is a grid of
  // checkboxes, where a first "None" is exclusive; "Other" in either shows a field for the user's own answer.
  const sections = [
    {
      title: 'About you',
      questions: [
        { key: 'position', kind: 'one', text: 'Your position', choices: ['Student', 'PhD student', 'Postdoc', 'Staff scientist', 'Instrument scientist', 'Professor or group leader', 'Industry', 'Other'] },
        { key: 'field', kind: 'one', text: 'Your field', choices: ['Physics', 'Chemistry', 'Materials science', 'Earth sciences', 'Biology', 'Engineering', 'Other'] },
        { key: 'experience', kind: 'one', text: 'Experience with diffraction data analysis', choices: ['None yet', 'Less than a year', '1 to 3 years', '3 to 10 years', 'More than 10 years'] },
        { key: 'tools', kind: 'many', text: 'Programs you use now', choices: ['None', 'FullProf', 'GSAS-II', 'TOPAS', 'JANA', 'Other'] },
      ],
    },
    {
      title: 'Ways to use EasyDiffraction',
      note: 'For each way of working: how interested you are, and how easy it was if you have tried it.',
      questions: [{ key: 'interfaces', kind: 'interfaces', rows: interfaces }],
    },
    {
      title: 'Your experience so far',
      questions: [
        { key: 'install', kind: 'rating', text: 'Installing and starting it', choices: ease, skip: 'Not tried' },
        { key: 'docs', kind: 'rating', text: 'Documentation and tutorials', choices: helpful, skip: 'Not read' },
        { key: 'features', kind: 'rating', text: 'How well the features fit your work', choices: fit, skip: 'Not sure' },
        { key: 'likely', kind: 'rating', text: 'How likely you are to use it for your work', choices: likely },
        { key: 'missing', kind: 'texts', count: 3, text: 'Up to three missing features you would need' },
        { key: 'wishes', kind: 'texts', count: 3, text: 'Up to three features that would be nice to have' },
      ],
    },
    {
      title: 'AI help',
      key: 'ai',
      questions: [
        { key: 'ai_interest', kind: 'rating', text: 'Your interest in AI help for diffraction', choices: interest, skip: 'Not interested, skip this section' },
        { key: 'ai_access', kind: 'one', text: 'How you would prefer to get access', choices: ['Sign in with my existing subscription', 'My own API key (pay per use)', 'Provided by my institution', 'Only if free', 'Not sure'] },
        { key: 'ai_data', kind: 'one', text: 'Sending your data to an AI provider is', choices: ['Fine', 'Fine without the measured data', 'Not allowed for my work', 'Not sure'] },
        { key: 'ai_assistant', kind: 'rating', text: "The app's built-in assistant, if you tried it", choices: quality, skip: "Didn't try" },
        { key: 'ai_uses', kind: 'many', text: 'How you would like to use it', choices: ["The app's built-in assistant", 'My own assistant writes notebooks', "Converting other programs' projects", 'Explaining fits or suggesting a strategy', 'Other'] },
        { key: 'ai_providers', kind: 'many', text: 'Providers you use or could use', choices: ['None', 'ChatGPT (OpenAI)', 'Claude (Anthropic)', 'GitHub Copilot', 'Gemini (Google)', 'A local or self-hosted model', 'A service from my institution', 'Other'] },
        { key: 'ai_assistant_note', kind: 'text', text: 'What worked or did not in the built-in assistant', wide: true },
      ],
    },
    {
      title: 'Anything else',
      questions: [
        { key: 'comments', kind: 'area', text: 'Anything else you would like to tell us' },
        { key: 'contact', kind: 'contact' },
      ],
    },
  ];

  const element = (tag, attributes = {}, children = []) => {
    const node = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) {
      if (name === 'text') node.textContent = value;
      else if (value !== false && value !== undefined) node.setAttribute(name, value === true ? '' : value);
    }
    node.append(...children);
    return node;
  };
  let uid = 0;
  const id = key => `survey-${key}-${++uid}`;

  function select(name, options, placeholder = 'Choose…') {
    const box = element('select', { name });
    box.add(new Option(placeholder, ''));
    for (const option of options) box.add(typeof option === 'string' ? new Option(option, option) : new Option(option.text, option.value));
    return box;
  }

  // The field for an "Other" answer, shown only while Other is chosen.
  function otherField(key) {
    return element('input', { type: 'text', name: `${key}_other`, placeholder: 'Your answer', 'aria-label': 'Other, your answer', maxlength: '200', hidden: true });
  }

  // A question as one cell of the grid: its label above its control.
  function field(q) {
    const cell = element('div', { class: `ed-survey-field${q.kind === 'many' || q.kind === 'texts' || q.kind === 'area' || q.wide ? ' ed-survey-wide' : ''}`, 'data-key': q.key });
    const controlId = id(q.key);
    cell.append(element('label', { class: 'ed-survey-label', for: controlId, text: q.text }));
    if (q.kind === 'one' || q.kind === 'rating') {
      const box = select(q.key, q.skip ? [...q.choices, { value: 'skip', text: q.skip }] : q.choices);
      box.id = controlId;
      cell.append(box);
      if (q.choices.includes('Other')) {
        const other = otherField(q.key);
        box.addEventListener('change', () => (other.hidden = box.value !== 'Other'));
        cell.append(other);
      }
    }
    if (q.kind === 'many') {
      const grid = element('div', { class: 'ed-survey-checks', id: controlId, role: 'group' });
      for (const choice of q.choices) grid.append(element('label', {}, [element('input', { type: 'checkbox', name: q.key, value: choice }), choice]));
      const other = q.choices.includes('Other') ? otherField(q.key) : null;
      grid.addEventListener('change', event => {
        const boxes = Array.from(grid.querySelectorAll('input'));
        // A first "None" is exclusive: ticking it clears the others, ticking another clears it.
        if (q.choices[0] === 'None' && event.target.checked) {
          if (event.target.value === 'None') boxes.slice(1).forEach(other => (other.checked = false));
          else boxes[0].checked = false;
        }
        if (other) other.hidden = !boxes.some(box => box.value === 'Other' && box.checked);
      });
      cell.append(grid);
      if (other) cell.append(other);
    }
    if (q.kind === 'texts') {
      const row = element('div', { class: 'ed-survey-texts' });  // one under another
      for (let i = 0; i < q.count; ++i) row.append(element('input', { type: 'text', name: q.key, id: i === 0 ? controlId : id(q.key), placeholder: `${i + 1}.`, 'aria-label': `${q.text}, ${i + 1}`, maxlength: '300' }));
      cell.append(row);
    }
    if (q.kind === 'text') cell.append(element('input', { type: 'text', name: q.key, id: controlId, maxlength: '500' }));
    if (q.kind === 'area') cell.append(element('textarea', { name: q.key, id: controlId, maxlength: '5000' }));

    return cell;
  }

  // Each interface: its name, then Interest and Ease of use side by side on the page's two columns. "Not tried" in
  // Ease of use answers whether it was tried.
  function interfaceFields(q) {
    // The two column titles once, above every interface.
    const titles = ['Interest', 'Ease of use'].map(text => element('span', { class: 'ed-survey-label ed-survey-minor ed-survey-coltitle', 'aria-hidden': 'true', text }));
    return [...titles, ...q.rows.flatMap(([key, label]) => {
      const heading = element('p', { class: 'ed-survey-subhead ed-survey-wide', text: label });
      const pair = [
        ['interest', 'Interest', interest],
        ['ease', 'Ease of use', [...ease, { value: 'skip', text: 'Not tried' }]],
      ].map(([what, title, options]) => {
        const box = select(`${what}_${key}`, options);
        box.id = id(`${what}_${key}`);
        box.setAttribute('aria-label', `${label}: ${title.toLowerCase()}`);
        return element('div', { class: 'ed-survey-field', 'data-key': `${what}_${key}` }, [box]);
      });
      return [heading, ...pair];
    })];
  }

  // The events open today, by the visitor's calendar date.
  function activeEvents(events, today) {
    return events.filter(event => (!event.start || event.start <= today) && (!event.end || today <= event.end));
  }

  function answers(form) {
    const data = new FormData(form);
    const text = name => String(data.get(name) || '').trim();
    const out = {};
    for (const section of sections) {
      for (const q of section.questions) {
        if (q.kind === 'interfaces') {
          for (const [key] of q.rows) {
            const ease = text(`ease_${key}`);
            const row = { interest: text(`interest_${key}`), tried: ease === 'skip' ? 'no' : ease ? 'yes' : '', ease: ease === 'skip' ? '' : ease };
            for (const name of Object.keys(row)) if (!row[name]) delete row[name];
            if (Object.keys(row).length) out[`interface_${key}`] = row;
          }
        } else if (q.kind === 'many' || q.kind === 'texts') {
          const values = data.getAll(q.key).map(value => String(value).trim()).filter(Boolean);
          if (values.length) out[q.key] = values;
        } else if (q.kind !== 'contact' && text(q.key)) {
          out[q.key] = text(q.key);
        }
        if (text(`${q.key}_other`) && (out[q.key] === 'Other' || (out[q.key] || []).includes?.('Other'))) out[`${q.key}_other`] = text(`${q.key}_other`);
      }
    }
    // "Not interested" in AI help leaves the rest of that section out.
    if (out.ai_interest === 'skip') for (const q of sections.find(s => s.key === 'ai').questions.slice(1)) delete out[q.key], delete out[`${q.key}_other`];
    return out;
  }

  // Name and e-mail side by side, then affiliation with the consent under the e-mail: inputs without a label above,
  // their placeholders saying what they are, as the Get in touch form's (the owner, 2026-11-10).
  function contactFields() {
    const words = (app && app.contact) || { name: 'Name (optional)', email: 'E-mail (optional)', affiliation: 'Affiliation (optional)' };
    const input = (type, name) => element('div', { class: 'ed-survey-field', 'data-key': name }, [element('input', { type, name, placeholder: words[name], 'aria-label': words[name] })]);
    return [
      input('text', 'name'),
      input('email', 'email'),
      input('text', 'affiliation'),
      element('div', { class: 'ed-survey-field ed-survey-consent-cell', 'data-key': 'consent' }, [
        element('label', { class: 'ed-survey-consent' }, [element('input', { type: 'checkbox', name: 'consent' }), 'You may e-mail me about my answers.']),
      ]),
    ];
  }

  function build(form, events) {
    const top = element('div', { class: 'ed-survey-grid' }, [
      element('div', { class: 'ed-survey-field ed-survey-wide', 'data-key': 'event' }, [element('label', { class: 'ed-survey-label', for: 'survey-event', text: 'Event' }), select('event', events.map(({ name, title }) => ({ value: name, text: title })), 'General')]),
    ]);
    top.querySelector('select').id = 'survey-event';
    top.querySelector('select').remove(0);
    form.append(top);
    for (const section of sections) {
      const part = element('section', { class: 'ed-survey-section', id: `survey-${section.key || section.title.toLowerCase().replace(/[^a-z]+/g, '-')}` }, [element('h2', { text: section.title })]);
      if (section.note) part.append(element('p', { class: 'ed-survey-note', text: section.note }));
      const grid = element('div', { class: 'ed-survey-grid' });
      for (const q of section.questions) grid.append(...(q.kind === 'interfaces' ? interfaceFields(q) : q.kind === 'contact' ? contactFields() : [field(q)]));
      part.append(grid);
      form.append(part);
    }
    // "Not interested" disables the rest of the AI section.
    const ai = form.querySelector('#survey-ai');
    form.elements.ai_interest.addEventListener('change', () => {
      const off = form.elements.ai_interest.value === 'skip';
      ai.querySelectorAll('input, select, textarea').forEach(control => control.name !== 'ai_interest' && (control.disabled = off));
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
        // Name and affiliation when filled in; the e-mail only with the consent to be contacted.
        const contact = {};
        for (const key of ['name', 'affiliation']) if (form.elements[key].value.trim()) contact[key] = form.elements[key].value.trim();
        if (form.elements.email.value.trim() && form.elements.consent.checked) contact.email = form.elements.email.value.trim();
        if (Object.keys(contact).length) message.contact = contact;
        pending = true;
        status.textContent = app.status.sending;
        let code = 0;
        try {
          code = (await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(message) })).status;
        } catch {
          code = 0;
        }
        status.textContent = code === 201 ? 'Thank you! Your answers were sent.' : code === 429 ? app.status.tooMany : code === 0 ? app.status.offline : app.status.failed.replace('%1', String(code));
        if (code === 201) {
          form.reset();
          form.querySelectorAll('[name$="_other"]').forEach(other => (other.hidden = true));
        }
        pending = false;
      });
    }
  }

  window.edSurvey = { sections, activeEvents, answers };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
  else setup();
  if (typeof document$ !== 'undefined') document$.subscribe(setup);
})();
