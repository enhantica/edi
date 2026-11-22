// The Get in touch form in a real browser: attach and drop files, the limits, Remove, the payload, and the answers
// (a 201 that does not confirm the files and keeps the contact details, a refusal), with fetch stubbed so nothing
// leaves the page. The notice has one button, Close: no Copy report.
const [url, chrome, playwright] = process.argv.slice(2);
const { chromium } = await import(playwright);
const browser = await chromium.launch({ executablePath: chrome, args: ['--no-sandbox', '--disable-gpu'] });
const page = await browser.newPage();
const errors = [];
page.on('pageerror', error => errors.push(String(error)));
await page.goto(url);
const failures = [];
const check = (condition, what) => { if (!condition) failures.push(what); };

// The answer the stub gives next, and every message it was sent.
await page.evaluate(() => {
  window.sent = [];
  window.reply = { status: 201, body: '{"number":1}' };
  window.fetch = async (address, options) => {
    window.sent.push(JSON.parse(options.body));
    return new Response(window.reply.body, { status: window.reply.status });
  };
});
const drop = (names, size = 4) => page.evaluate(([names, size]) => {
  const transfer = new DataTransfer();
  for (const name of names) transfer.items.add(new File([new Uint8Array(size).fill(65)], name, { type: name.endsWith('.png') ? 'image/png' : '' }));
  const form = document.querySelector('form.ed-contact-form');
  form.dispatchEvent(new DragEvent('dragover', { dataTransfer: transfer, bubbles: true, cancelable: true }));
  form.dispatchEvent(new DragEvent('drop', { dataTransfer: transfer, bubbles: true, cancelable: true }));
}, [names, size]);
const state = () => page.evaluate(() => ({
  items: Array.from(document.querySelectorAll('.ed-contact-file-list li')).map(item => item.firstChild.textContent),
  error: document.querySelector('.ed-contact-file-error').textContent,
  sendDisabled: document.querySelector('form.ed-contact-form button[type="submit"]').disabled,
}));

// The link: under the message at the left, the app's tooltip, the paperclip; no note under Send.
const layout = await page.evaluate(() => {
  const link = document.querySelector('.ed-contact-attach');
  const message = document.querySelector('textarea[name="message"]').getBoundingClientRect();
  const box = link.getBoundingClientRect();
  return {
    text: link.textContent, title: link.title, svg: Boolean(link.querySelector('svg')),
    under: box.top >= message.bottom, left: Math.abs(box.left - message.left) < 2,
    note: document.querySelector('.ed-contact-note'),
  };
});
check(layout.text === 'Attach files' && layout.svg, `the link reads Attach files with a paperclip: ${JSON.stringify(layout)}`);
check(layout.title.includes('up to 5 files, 5 MB each, 10 MB in total') && layout.title.includes('dropped on the form'), 'the tooltip is the app\'s');
check(layout.under && layout.left, 'the link is under the message, at the left');
check(layout.note === null, 'no note under Send');

// Drop, list, Remove, and the limits.
await drop(['hrpt.xye', 'lbco.cif']);
await page.waitForFunction(() => document.querySelectorAll('.ed-contact-file-list li').length === 2);
check((await state()).items.join('|') === 'hrpt.xye · 4 B|lbco.cif · 4 B', 'both dropped files are listed with their sizes');
await page.click('.ed-contact-file-list li:first-child .ed-contact-remove');
check((await state()).items.join('|') === 'lbco.cif · 4 B', 'Remove takes a file off the list');
await drop(['a.txt', 'b.txt', 'c.txt', 'd.txt', 'e.txt']);
await page.waitForFunction(() => document.querySelectorAll('.ed-contact-file-list li').length === 6);
let now = await state();
check(now.error === 'Not sent: at most 5 files can be attached. Remove a file to send.' && now.sendDisabled, `six files are refused naming the limit: ${JSON.stringify(now)}`);
await page.click('.ed-contact-file-list li:first-child .ed-contact-remove');
now = await state();
check(now.error === '' && !now.sendDisabled, 'five files may be sent');

// A 201 that does not confirm the files says which were not attached, and keeps the contact details.
await page.fill('input[name="name"]', 'Ada');
await page.fill('input[name="email"]', 'ada@example.org');
await page.fill('input[name="subject"]', 'Files');
await page.fill('textarea[name="message"]', 'Cannot read my files');
await page.click('form.ed-contact-form button[type="submit"]');
await page.waitForSelector('dialog.ed-contact-notice[open]');
const buttons = () => page.evaluate(() => Array.from(document.querySelectorAll('dialog.ed-contact-notice button'))
  .filter(button => button.getClientRects().length).map(button => button.textContent));
const first = await page.evaluate(() => ({ text: document.querySelector('dialog.ed-contact-notice p').textContent, message: window.sent[0] }));
check(first.message.attachments.length === 5 && first.message.attachments[0].data === btoa('AAAA'), 'the files go as the app sends them');
check(first.text === 'Your message was sent. Thank you! But a.txt, b.txt, c.txt, d.txt, e.txt were not attached. Your name, e-mail and affiliation are kept, so you can send another message.', `unconfirmed files: ${first.text}`);
check((await buttons()).join('|') === 'Close', `only Close after a success: ${(await buttons()).join('|')}`);
const kept = await page.evaluate(() => ['name', 'email', 'subject', 'message'].map(key => document.querySelector(`form.ed-contact-form [name="${key}"]`).value));
check(kept.join('|') === 'Ada|ada@example.org||', `a sent message keeps name and e-mail, clears subject and text: ${kept.join('|')}`);
check((await state()).items.length === 0, 'a sent message clears the files');
await page.click('dialog.ed-contact-notice button:last-child');

// A refusal says why; the text and files stay.
await page.evaluate(() => (window.reply = { status: 502, body: '{"error":"the message could not be stored (GitHub 422), try again later"}' }));
await drop(['lbco.cif']);
await page.fill('textarea[name="message"]', 'Second try');
await page.click('form.ed-contact-form button[type="submit"]');
await page.waitForSelector('dialog.ed-contact-notice[open]');
const second = await page.evaluate(() => ({ text: document.querySelector('dialog.ed-contact-notice p').textContent }));
check(second.text === 'The feedback service did not take the message (502): the message could not be stored (GitHub 422), try again later', `refusal: ${second.text}`);
check((await buttons()).join('|') === 'Close', `only Close after a refusal: ${(await buttons()).join('|')}`);
check((await state()).items.length === 1 && (await page.inputValue('textarea[name="message"]')) === 'Second try', 'a failed send keeps the text and files');

check(errors.length === 0, `no page errors: ${errors.join('; ')}`);
await browser.close();
if (failures.length) {
  console.error('contact_form: FAIL\n- ' + failures.join('\n- '));
  process.exit(1);
}
console.log('contact_form: PASS');
