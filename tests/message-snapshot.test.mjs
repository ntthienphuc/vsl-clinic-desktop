import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import ts from 'typescript';

const source = await fs.readFile(path.resolve('src/messageSnapshot.ts'), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } });
const { MessageSnapshotCache } = await import('data:text/javascript;base64,' + Buffer.from(compiled.outputText).toString('base64'));
const original = [{ id: 'word-1', role: 'patient', text: 'Bụng', status: 'streaming', predictions: [{ gloss: 'Bụng', score: .6 }, { gloss: 'Đau', score: .3 }], words: [{ id: 'part-1', text: 'Bụng' }] }];
const clone = value => JSON.parse(JSON.stringify(value));

test('capture-only snapshots reuse history, while corrections and ranked candidates invalidate it', () => {
  const cache = new MessageSnapshotCache();
  const first = cache.accept('session-1', clone(original));
  for (let i = 0; i < 200; i++) assert.equal(cache.accept('session-1', clone(original)), first);
  for (const change of [
    value => { value[0].text = 'Đau bụng'; },
    value => { value[0].status = 'completed'; },
    value => { value[0].predictions[1].gloss = 'Nóng'; },
    value => { value[0].words[0].text = 'Đau'; },
    value => { value[0].speech_repair = { raw_text: 'bụn', corrected_text: 'bụng' }; },
  ]) {
    const next = clone(original); change(next);
    const cached = cache.accept('session-1', next);
    assert.notEqual(cached, first);
    assert.deepEqual(cached, next);
    const restored = clone(original);
    assert.equal(cache.accept('session-1', restored), restored);
  }
});

test('a new session replaces the cached history, including an empty reset', () => {
  const cache = new MessageSnapshotCache();
  const first = cache.accept('session-1', clone(original));
  const second = cache.accept('session-2', clone(original));
  assert.notEqual(first, second);
  const empty = cache.accept('session-3', []);
  assert.deepEqual(empty, []);
  assert.equal(cache.accept('session-3', []), empty);
  assert.notEqual(cache.accept('session-4', []), empty);
});
