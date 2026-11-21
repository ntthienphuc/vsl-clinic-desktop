import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
import ts from 'typescript';

const root = path.resolve(import.meta.dirname, '..');
const folder = path.join(root, 'build/test-avatar-modules'), output = path.join(folder, 'motionLibrary.mjs');
await fs.mkdir(folder, { recursive: true });
for (const name of ['kinematics', 'packedMotion', 'curatedHands', 'motionLibrary']) {
  let source = await fs.readFile(path.join(root, 'src/avatar', name + '.ts'), 'utf8');
  source = source.replace("import curation from '../../assets/motions/hand-curation.json';", 'const curation = ' + await fs.readFile(path.join(root, 'assets/motions/hand-curation.json'), 'utf8') + ';');
  let js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  for (const dependency of ['kinematics', 'packedMotion', 'curatedHands']) js = js.replace(`'./${dependency}'`, `'./${dependency}.mjs'`);
  await fs.writeFile(path.join(folder, name + '.mjs'), js);
}
const { MotionLibrary } = await import(pathToFileURL(output));
const { decodePackedMotion } = await import(pathToFileURL(path.join(folder, 'packedMotion.mjs')));
const { curateHands } = await import(pathToFileURL(path.join(folder, 'curatedHands.mjs')));

test('every packed motion decodes with bounded point error and unchanged identity', async () => {
  const manifest = JSON.parse(await fs.readFile(path.join(root, 'assets/motions/manifest.json'), 'utf8'));
  for (const entry of manifest.entries) {
    const original = JSON.parse(await fs.readFile(path.join(root, 'assets/motions', entry.id + '.json'), 'utf8'));
    const bytes = await fs.readFile(path.join(root, 'assets/motions', entry.id + '.vslm'));
    const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    const decoded = decodePackedMotion(buffer);
    assert.equal(decoded.id, original.id); assert.equal(decoded.label, original.label);
    assert.equal(decoded.duration_ms, original.duration_ms); assert.deepEqual(decoded.source_hashes, original.source_hashes);
    assert.equal(decoded.frames.length, original.frames.length);
    for (let f = 0; f < decoded.frames.length; f++) for (let p = 0; p < 75; p++) for (let a = 0; a < 3; a++) {
      assert.ok(Math.abs(decoded.frames[f][p][a] - original.frames[f][p][a]) <= .0001, entry.id);
    }
    assert.throws(() => decodePackedMotion(buffer.slice(0, buffer.byteLength - 1)));
  }
});

test('curation preserves raw poses, body/wrist tracks and rejects unrelated source hashes', async () => {
  for (const id of ['11', 'qipedc-W00362', '391']) {
    const original = JSON.parse(await fs.readFile(path.join(root, 'assets/motions', id + '.json'), 'utf8'));
    const untouched = structuredClone(original), curated = curateHands(original);
    assert.deepEqual(original, untouched); assert.notDeepEqual(curated.frames, original.frames);
    for (let f = 0; f < original.frames.length; f++) {
      assert.deepEqual(curated.frames[f].slice(0, 33), original.frames[f].slice(0, 33));
      assert.deepEqual(curated.frames[f][33], original.frames[f][33]); assert.deepEqual(curated.frames[f][54], original.frames[f][54]);
    }
    const unrelated = { ...original, source_hashes: ['different-source'] };
    assert.equal(curateHands(unrelated), unrelated);
  }
});

test('motions load on demand, share in-flight requests, retain original data and evict unused clips', async () => {
  const previous = globalThis.fetch, calls = [], pending = new Map();
  globalThis.fetch = (url) => new Promise(resolve => { calls.push(url); pending.set(url, resolve); });
  const library = new MotionLibrary(['a', 'b', 'c'].map(id => ({ id, path: id })), 2);
  try {
    assert.equal(calls.length, 0);
    let ready = false;
    const first = library.prepare(['a', 'a', 'b']).then(() => { ready = true; });
    const same = library.prepare(['a', 'b']);
    assert.deepEqual(calls, ['a', 'b']);
    assert.equal(ready, false);
    for (const id of ['a', 'b']) pending.get(id)({ ok: true, json: async () => ({ id, frames: [[[1.23456789, 2, 3]]] }) });
    await Promise.all([first, same]);
    assert.equal(ready, true);
    assert.equal(library.motions.get('a').frames[0][0][0], 1.23456789);
    const next = library.prepare(['b', 'c']);
    pending.get('c')({ ok: true, json: async () => ({ id: 'c', frames: [[[0, 0, 0]]] }) });
    await next;
    assert.deepEqual([...library.motions.keys()], ['b', 'c']);
    await assert.rejects(library.prepare(['missing']));
    library.dispose();
    assert.equal(library.motions.size, 0);
  } finally { globalThis.fetch = previous; library.dispose(); }
});
