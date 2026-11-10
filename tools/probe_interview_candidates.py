"""Choose a labelled practice reference after documenting a failed demo clip.

This is rehearsal selection, not a held-out recognition evaluation.
"""
import asyncio
import hashlib
import json
from pathlib import Path

import httpx
from build_rehearsal_kit import composite

ROOT = Path(__file__).resolve().parents[1]


async def main():
    source = next(w for w in json.loads((ROOT/'research/source-manifest.json').read_text(encoding='utf-8'))['words'] if w['id']=='150')
    refs = [source['demo_source'], *[r for r in source['references'] if r['video_id'] in {'021368','022152','023036','023920'}]]
    folder = ROOT/'research/cache/interview-candidates'; folder.mkdir(parents=True,exist_ok=True)
    async with httpx.AsyncClient(timeout=45) as raw:
        targets=(await raw.get('http://127.0.0.1:58901/json')).json()
    from urllib.parse import urlparse,parse_qs
    url=urlparse(next(t['url'] for t in targets if '/doctor?' in t['url']))
    token=parse_qs(url.query)['token'][0]
    report={'scope':'Selection of labelled fixed-video rehearsal references, not unbiased accuracy. Inference receives video bytes only.','rows':[]}
    async with httpx.AsyncClient(base_url=f'{url.scheme}://{url.netloc}',headers={'Authorization':'Bearer '+token},timeout=45) as c:
        await c.post('/api/conversation/stop',json={})
        for ref in refs:
            original=Path(ref['path']); assert hashlib.sha256(original.read_bytes()).hexdigest()==ref['sha256']
            clip=folder/(ref['video_id']+'.mp4'); metadata=composite([original],clip)
            await c.post('/api/session/reset',json={})
            with clip.open('rb') as f: r=await c.post('/api/capture/upload',files={'file':('candidate.mp4',f,'video/mp4')})
            r.raise_for_status(); generation=r.json()['generation']
            for _ in range(500):
                state=(await c.get('/api/diagnostics')).json()['state']
                if state['capture'].get('generation')==generation and state['capture']['status']=='ended' and state['patient_turn'] is None: break
                await asyncio.sleep(.08)
            words=[w for m in state['messages'] for w in m.get('words',[])]
            row={'video_id':ref['video_id'],'label':ref['gloss'],'source_sha256':ref['sha256'],'replay':metadata,'actual':[w['text'] for w in words], 'words':words}
            report['rows'].append(row)
            print(json.dumps({'video_id':row['video_id'],'actual':row['actual']},ensure_ascii=False),flush=True)
            (ROOT/'docs/evidence/interview-reference-selection-2026-11-01.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        await c.post('/api/capture/stop',json={})


if __name__=='__main__': asyncio.run(main())
