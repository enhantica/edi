// SPDX-License-Identifier: BSD-3-Clause
// Run against the actual Worker entry module: node --test worker-issue-labels.mjs
// with FEEDBACK_WORKER_SOURCE pointing to that module's local file.
import assert from 'node:assert/strict';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {test} from 'node:test';

const labels = ['[scope] ⚠️ label needed', '[priority] ⚠️ label needed'].sort();

for (const repository of ['example/private-feedback', 'example/public-app']) {
  test(`issue request to ${repository} carries exactly the provisional labels`, async context => {
    const source = process.env.FEEDBACK_WORKER_SOURCE;
    assert.ok(source, 'The offline gate requires the actual Worker entry module');
    const requests = [];
    context.mock.method(globalThis, 'fetch', async (url, init) => {
      assert.equal(String(url), `https://api.github.com/repos/${repository}/issues`,
        'The Worker sends only its issue-creation request to the selected repository');
      assert.equal(init.method, 'POST', 'The Worker sends the issue payload as a POST');
      requests.push(JSON.parse(init.body));
      return Response.json({number: 314}, {status: 201});
    });
    const {default: worker} = await import(pathToFileURL(resolve(source)).href);
    const submissions = [
      ['feedback', {kind: 'feedback', text: 'A message from the shared form.'}, 'A message from the shared form.'],
      ['feedback', {kind: 'problem', text: 'A diagnostic from an existing client.'}, 'A diagnostic from an existing client.'],
      ['feedback', {kind: 'likes', answer: 'yes'}, 'Enjoying EasyDiffraction?'],
      ['survey', {event: 'general', answers: {purpose: 'Teaching'}}, 'Teaching'],
    ];
    for (const [route, message] of submissions) {
      const request = new Request(`https://feedback.example.invalid/${route}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(message),
      });
      const response = await worker.fetch(request, {
        REPO: repository,
        GITHUB_TOKEN: 'offline-test-token',
        LIMITER: {limit: async () => ({success: true})},
      });
      assert.equal(response.status, 201, 'Each valid submission reaches the issue builder');
    }
    assert.equal(requests.length, submissions.length, 'Each submission files one issue');
    for (const [index, payload] of requests.entries())
      assert.ok(payload.body.includes(submissions[index][2]), 'The issue contains its own submission');
    assert.deepEqual(requests.map(({labels}) => [...labels].sort()), submissions.map(() => labels),
      'Every issue payload has exactly the two provisional labels');
  });
}
