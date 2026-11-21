"""Public synthetic doctor utterances through the packaged live ASR socket."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

import httpx
import numpy as np
from faster_whisper.audio import decode_audio
from websockets.asyncio.client import connect

async def main(args):
    args.output.mkdir(parents=True, exist_ok=True)
    cases = [('Đồng ý nằm nghỉ ngơi', ['Đồng ý', 'Nằm', 'Nghỉ ngơi']),
             ('Bạn có đau mắt không?', ['Đau mắt']),
             ('Bạn cần đi vệ sinh không?', ['Cần', 'Nhà vệ sinh', 'Đi'])]
    fixtures = []
    for index, (text, expected) in enumerate(cases):
        file = args.output / f'public-synthetic-{index}.mp3'
        source = 'https://translate.google.com/translate_tts?' + urllib.parse.urlencode({'ie':'UTF-8','client':'tw-ob','tl':'vi','q':text})
        if not file.exists():
            with urllib.request.urlopen(urllib.request.Request(source, headers={'User-Agent':'Mozilla/5.0'}), timeout=30) as response:
                assert 'audio' in response.headers.get('Content-Type', '')
                file.write_bytes(response.read(2 * 1024 * 1024))
        fixtures.append({'text':text,'expected':expected,'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    async with httpx.AsyncClient(timeout=45) as client:
        pages = (await client.get(f'http://127.0.0.1:{args.port}/json')).json()
        doctor = next(page for page in pages if '/doctor?' in page['url'])
        parsed = urllib.parse.urlsplit(doctor['url'])
        token = urllib.parse.parse_qs(parsed.query)['token'][0]
        origin = f'{parsed.scheme}://{parsed.netloc}'
        async def api(route, body=None):
            response = await client.request('POST' if body is not None else 'GET', origin+'/api'+route,
                                          headers={'Authorization':'Bearer '+token},json=body)
            response.raise_for_status()
            return response.json()
        async def state(): return (await api('/diagnostics'))['state']
        await api('/session/reset', {})
        await api('/conversation/configure', {'mode':'auto','source':{'kind':'demo','demo_id':'mm100:W068'}})
        await api('/conversation/start', {})
        await api('/capture/stop', {})
        # The test's websocket owns synthetic audio; disable the fake UI mic first.
        async with connect(doctor['webSocketDebuggerUrl']) as cdp:
            for attempt in range(40):
                await cdp.send(json.dumps({'id':attempt+1,'method':'Runtime.evaluate','params':{'expression':"(()=>{const b=[...document.querySelectorAll('.live-speech-status button')].find(b=>b.textContent.trim()==='Tắt micro'); if(b&&!b.disabled){b.click();return true;}return false;})()",'returnByValue':True}}))
                reply=json.loads(await cdp.recv())
                if reply.get('result',{}).get('result',{}).get('value'):break
                await asyncio.sleep(.2)
            else: raise RuntimeError('Could not mute fake UI microphone')
        # The UI sends a graceful cancel; wait for the engine's socket owner to
        # release rather than racing it with the synthetic microphone.
        await asyncio.sleep(2)
        rows=[]
        try:
            for fixture in fixtures:
                before=await state();old={m['id'] for m in before['messages']};old_drafts={m['id'] for m in before['speech_drafts']}
                samples=decode_audio(str(args.output/fixture['file']), sampling_rate=16000)
                pcm=(np.clip(samples,-1,1)*32767).astype('<i2').tobytes();events=[]
                async with connect(origin.replace('http://','ws://')+'/ws/speech?live=true&token='+token) as socket:
                    while True:
                        event=json.loads(await asyncio.wait_for(socket.recv(),60))
                        if event['type']=='error':raise RuntimeError(event)
                        if event['type']=='ready':break
                    async def receive():
                        async for data in socket:
                            event=json.loads(data);events.append(event)
                            if event['type']=='finished':return
                            if event['type']=='error':raise RuntimeError(event)
                    reader=asyncio.create_task(receive());data=bytes(16000)+pcm+bytes(32000*4);started=time.monotonic()
                    for offset in range(0,len(data),3200):
                        await asyncio.sleep(max(0,started+offset/32000-time.monotonic()));await socket.send(data[offset:offset+3200])
                    await socket.send(json.dumps({'action':'finish'}));await asyncio.wait_for(reader,45)
                current=await state();sent=[m for m in current['messages'] if m['id'] not in old and m['role']=='doctor'];drafts=[m for m in current['speech_drafts'] if m['id'] not in old_drafts]
                transcripts=[e for e in events if e['type']=='transcript'];actual=[[g['label'] for g in m['glosses']] for m in sent]
                row={**fixture,'transcripts':transcripts,'sent_glosses':actual,'drafts':drafts,
                     'passed':len(transcripts)==1 and actual==[fixture['expected']] and not drafts}
                rows.append(row);print(json.dumps({'text':fixture['text'],'heard':[e.get('text') for e in transcripts],'sent_glosses':actual,'passed':row['passed']},ensure_ascii=False),flush=True)
                end=time.monotonic()+40
                while time.monotonic()<end and (await state()).get('playback',{}).get('status') in {'loading','playing'}:await asyncio.sleep(.2)
            report={'passed':all(row['passed'] for row in rows),'rows':rows,'scope':'Three public synthetic voices with four-second silent tails through actual EXE live ASR. No human microphone or clinic-noise claim.'}
            (args.output/'speech.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
        finally:await api('/session/reset',{})

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=58964);parser.add_argument('--output',type=Path,required=True)
    asyncio.run(main(parser.parse_args()))
