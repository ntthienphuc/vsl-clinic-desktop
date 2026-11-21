/* Render and exercise the actual Electron pages, isolated public-fixture profile. */
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const args=Object.fromEntries(process.argv.slice(2).map(s=>s.replace(/^--/,'').split('=')));
const out=path.resolve(args.output);
fs.mkdirSync(out,{recursive:true});
const sockets=[];
const report={scope:'Real Electron rendering and UI interactions; no live user or clinical validation',checks:{},layouts:[]};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,limit=20000){const start=Date.now();while(Date.now()-start<limit){const value=await fn();if(value)return value;await delay(100);}throw Error('Timeout: '+fn.toString().slice(0,120));}
async function connect(target){
 const ws=new WebSocket(target.webSocketDebuggerUrl);sockets.push(ws);
 await new Promise((r,j)=>{ws.addEventListener('open',r,{once:true});ws.addEventListener('error',j,{once:true});});
 let seq=0;const pending=new Map();
 ws.addEventListener('message',e=>{const v=JSON.parse(e.data);pending.get(v.id)?.(v);});
 const call=async(method,params={})=>{const id=++seq;let timer;const wait=new Promise((r,j)=>{pending.set(id,r);timer=setTimeout(()=>j(Error(method)),15000);});ws.send(JSON.stringify({id,method,params}));const v=await wait.finally(()=>{clearTimeout(timer);pending.delete(id);});if(v.error)throw Error(JSON.stringify(v.error));return v.result;};
 const evaluate=async expression=>{const v=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(v.exceptionDetails)throw Error(JSON.stringify(v.exceptionDetails));return v.result.value;};
 return {call,eval:evaluate,shot:async name=>{const v=await call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(v.data,'base64'));}};
}
try{
 const pages=await(await fetch('http://127.0.0.1:'+(args.port||58970)+'/json')).json();
 const doctorTarget=pages.find(p=>p.url.includes('/doctor?'));
 const doctor=await connect(doctorTarget),patient=await connect(pages.find(p=>p.url.includes('/patient?')));
 const url=new URL(doctorTarget.url);
 const headers={Authorization:'Bearer '+url.searchParams.get('token'),'Content-Type':'application/json'};
 const api=async(route,body)=>{const r=await fetch(url.origin+'/api'+route,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:JSON.stringify(body)});assert.ok(r.ok,route+': '+r.status);return r.json();};
 await until(()=>doctor.eval("!!document.querySelector('.composer-card')"));
 report.version=(await(await fetch(url.origin+'/healthcheck')).json()).version;
 const bootstrap=await api('/bootstrap');report.vocabulary=bootstrap.vocabulary.length;report.phrases=bootstrap.quick_phrases.length;
 assert.equal(report.vocabulary,Number(args.vocabulary || 200));
 assert.equal(await patient.eval("document.querySelectorAll('button,a,input,textarea,select,[role=button]').length"),0);
 report.checks.passivePatient=true;
 for(const [width,height] of [[375,812],[570,780],[754,779],[768,1024],[1440,900]]){
   for(const [role,page] of [['doctor',doctor],['patient',patient]]){
    await page.call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});await delay(160);
    const layout=await page.eval("({width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight})");
    report.layouts.push({role,...layout});
    assert.ok(layout.scrollWidth<=width+1,role+' horizontal overflow '+JSON.stringify(layout));
    if(width>=700)assert.ok(layout.scrollHeight<=height+1,role+' vertical desktop overflow '+JSON.stringify(layout));
    await page.shot(role+'-'+width);
   }
 }
 await doctor.call('Emulation.setDeviceMetricsOverride',{width:754,height:779,deviceScaleFactor:1,mobile:false});
 await doctor.eval("(()=>{const b=document.querySelector('.quick-phrases button');b.focus();b.click();return true})()");
 await until(()=>doctor.eval("!!document.querySelector('dialog[open]')"));
 assert.equal(await doctor.eval("document.querySelectorAll('.library-phrase-list button').length"),8);
 assert.equal(await doctor.eval("document.querySelector('dialog .library-words, dialog .dictionary-stage')"),null);
 await doctor.eval("document.querySelector('.phrase-filter select').value='Khám và đo';document.querySelector('.phrase-filter select').dispatchEvent(new Event('change',{bubbles:true}))");
 await until(()=>doctor.eval("document.querySelector('.library-result-heading h3').textContent==='Khám và đo'"));
 assert.ok(await doctor.eval("[...document.querySelectorAll('.library-phrase-list small')].every(s=>s.textContent==='Khám và đo')"));
 await doctor.eval("document.querySelector('.phrase-filter select').value='Hay dùng';document.querySelector('.phrase-filter select').dispatchEvent(new Event('change',{bubbles:true}))");
 await until(()=>doctor.eval("document.querySelectorAll('.library-phrase-list button').length===8"));
 report.checks.libraryTaskFilterAndDedicatedDictionary=true;
 await doctor.shot('library-common-754');
 const search=async value=>doctor.eval(`(()=>{const input=document.querySelector('.library-search input');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,${JSON.stringify(value)});input.dispatchEvent(new Event('input',{bubbles:true}));return true})()`);
 await search('dau bung');await delay(150);
 assert.ok(await doctor.eval("document.querySelector('.library-phrase-list').textContent.includes('bụng')"));
 await doctor.shot('library-search');
 await search('zz-no-results');await delay(150);
 assert.ok(await doctor.eval("!!document.querySelector('.library-empty')"));
 report.checks.accentInsensitiveSearchAndEmpty=true;
 await doctor.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
 await doctor.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
 await until(()=>doctor.eval("!document.querySelector('dialog[open]')"));
 assert.ok(await doctor.eval("document.activeElement.closest('.quick-phrases')!==null"));
 report.checks.escapeFocusRestoration=true;
 await doctor.eval("document.querySelector('[data-testid=interface-language]').click()");
 await until(()=>doctor.eval("document.documentElement.lang==='en'"));
 await until(()=>patient.eval("document.documentElement.lang==='en'"));
 await doctor.eval("[...document.querySelectorAll('.quick-phrases button')][0].click()");await delay(100);
 assert.ok(await doctor.eval("document.querySelector('dialog').textContent.includes('Common phrases') || document.querySelector('dialog').textContent.includes('Frequently used')"));
 await doctor.shot('library-english');
 await doctor.call('Emulation.setDeviceMetricsOverride',{width:375,height:812,deviceScaleFactor:1,mobile:false});await delay(100);
 assert.ok(await doctor.eval("document.documentElement.scrollWidth<=innerWidth && document.querySelector('dialog').scrollWidth<=innerWidth"));
 await doctor.shot('library-english-375');
 await doctor.eval("document.querySelector('.sheet-heading button').click()");
 await doctor.eval("document.querySelector('[data-testid=interface-language]').click()");
 await until(()=>doctor.eval("document.documentElement.lang==='vi'"));
 report.checks.sharedLocaleAndNarrowModal=true;
 await doctor.call('Emulation.setDeviceMetricsOverride',{width:754,height:779,deviceScaleFactor:1,mobile:false});
 await doctor.call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
 assert.equal(await doctor.eval("getComputedStyle(document.querySelector('button')).transitionDuration"),'0s');
 report.checks.reducedMotion=true;
 await doctor.call('Emulation.setEmulatedMedia',{features:[]});
 await doctor.eval("document.querySelector('.settings-trigger').click()");
 await delay(120);await doctor.shot('settings');
 assert.equal(await doctor.eval("document.querySelectorAll('.recognition-mode-options button').length"),2);
 await doctor.eval("document.querySelector('.sheet-heading button').click()");
 report.checks.doctorOnlyModeSettings=true;
 await doctor.eval("document.querySelector('.display-menu > button').click()");
 assert.equal(await doctor.eval("document.querySelector('.display-menu > button').getAttribute('aria-expanded')"),'true');
 await doctor.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
 await doctor.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
 await until(()=>doctor.eval("!document.querySelector('.dropdown')"));
 assert.equal(await doctor.eval("document.activeElement.getAttribute('aria-label')"),'Bố trí màn hình');
 report.checks.displayMenuKeyboard=true;
 for(const text of ['Bạn có đau bụng không?','Bạn cần gối không?','Bạn có cần chăn không?','Bạn muốn rửa mặt không?','Bạn có muốn uống nước ấm không?']){
   const plan=await api('/text/plan',{text});assert.ok(plan.supported,text);
 }
 report.checks.newPhrasePlanning=true;
 await api('/session/reset',{});
 await until(()=>doctor.eval("document.querySelectorAll('.quick-send-row button').length===3"));
 const buttons=await doctor.eval("[...document.querySelectorAll('.quick-send-row button')].map(b=>b.textContent)");
 assert.deepEqual(buttons,['Bạn có đau không?','Y tá đo nhiệt độ.','Ngồi nghỉ ngơi.']);
 await doctor.eval("(()=>{const el=document.querySelector('#doctor-message-input');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(el,'Đang soạn');el.dispatchEvent(new Event('input',{bubbles:true}));const b=document.querySelectorAll('.quick-send-row button')[1];b.click();b.click();return true})()");
 await until(async()=>(await api('/diagnostics')).state.messages.some(m=>m.role==='doctor'&&m.text===buttons[1]));
 assert.equal((await api('/diagnostics')).state.messages.filter(m=>m.role==='doctor'&&m.text===buttons[1]).length,1);
 assert.equal(await doctor.eval("document.querySelector('#doctor-message-input').value"),'Đang soạn');
 await api('/session/reset',{});
 report.checks.inlineQuickSendPreservesDraftAndSendsOnce=true;
 report.passed=true;
}catch(error){report.error=error.stack;process.exitCode=1;}
finally{for(const socket of sockets)socket.close();fs.writeFileSync(path.join(out,'ui-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));}
