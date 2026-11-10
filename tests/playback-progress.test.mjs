import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
import ts from 'typescript';

const root=path.resolve(import.meta.dirname,'..'), out=path.join(root,'build/progress-tests');
await fs.mkdir(out,{recursive:true});
for(const [name,source] of [['motion','src/avatar/motion.ts'],['progress','src/playbackProgress.ts']]) {
  const compiled=ts.transpileModule(await fs.readFile(path.join(root,source),'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;
  await fs.writeFile(path.join(out,name+'.mjs'),compiled.replace("'./avatar/motion'","'./motion.mjs'"));
}
const {playbackProgress}=await import(pathToFileURL(path.join(out,'progress.mjs')));
const playback={status:'playing',elapsed_ms:0,started_at_ms:1000,total_ms:4000,rate:1,glosses:[{label:'Bác sĩ'},{label:'Nhiệt độ'},{label:'Đo'}],timeline:[{start_ms:0,end_ms:1000,index:0,phase:'sign'},{start_ms:1000,end_ms:1200,index:0,phase:'bridge'},{start_ms:1200,end_ms:2700,index:1,phase:'sign'},{start_ms:2700,end_ms:4000,index:2,phase:'sign'}]};
test('doctor progress follows the current sign, bridge and playback rate',()=>{
 assert.equal(playbackProgress(playback,1500).label,'Bác sĩ');
 assert.equal(playbackProgress(playback,2100).phase,'bridge');
 assert.equal(playbackProgress(playback,2500).label,'Nhiệt độ');
 assert.equal(playbackProgress({...playback,rate:2},2500).label,'Đo');
 assert.equal(playbackProgress({...playback,rate:.5},2500).remainingSeconds,7);
});
test('pause and disconnect freeze progress; loading and replay begin at zero',()=>{
 const paused={...playback,status:'paused',elapsed_ms:1500};
 assert.equal(playbackProgress(paused,9000).percent,37.5);
 assert.equal(playbackProgress(paused,99000).percent,37.5);
 assert.equal(playbackProgress({...playback,status:'loading',elapsed_ms:1500},99000).percent,0);
 assert.equal(playbackProgress({...playback,started_at_ms:9000},9000).percent,0);
});
test('completed reaches 100 percent; stopped preserves actual progress',()=>{
 assert.equal(playbackProgress({...playback,status:'completed'},1000).percent,100);
 assert.equal(playbackProgress({...playback,status:'stopped',elapsed_ms:1500},99000).percent,37.5);
 assert.equal(playbackProgress(playback,99000).percent,100);
});
