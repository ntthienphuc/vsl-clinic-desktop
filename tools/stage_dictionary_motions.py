"""Resume a bounded batch of source-backed QIPEDC candidates outside the app.

Never changes vocabulary/recognizer/runtime manifests. Review records and source
hashes are needed before deleting temporary downloads or promoting a motion.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'research/cache/dictionary-expansion'

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),'utf8');temp.replace(path)

def source_sheet(video,target,label):
    cap=cv2.VideoCapture(str(video));count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=cap.get(cv2.CAP_PROP_FPS)
    if count<8 or not fps>0:cap.release();raise ValueError('Invalid source video')
    sheet=Image.new('RGB',(1440,1040),'#f5f6f2');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
    draw.text((12,5),label+' / source timeline',font=font,fill='#23483b')
    decoded=0
    try:
        for tile,index in enumerate(np.linspace(0,count-1,24).astype(int)):
            cap.set(cv2.CAP_PROP_POS_FRAMES,int(index));ok,frame=cap.read()
            if not ok:raise ValueError('Source decode failed')
            decoded+=1
            # Crop unused video edges while retaining full head/arms/torso.
            h,w=frame.shape[:2];frame=frame[int(h*.02):int(h*.98),int(w*.1):int(w*.9)]
            im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));im.thumbnail((236,220))
            x=(tile%6)*240+(240-im.width)//2;y=36+(tile//6)*250
            sheet.paste(im,(x,y));draw.text(((tile%6)*240+6,y+220),f'{index/fps:.2f}s',font=font,fill='#23483b')
        sheet.save(target,quality=90)
    finally:cap.release()
    return {'frames':count,'fps':fps,'timeline_samples':decoded}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract',action='store_true',help='Download/extract at most --limit new candidates; otherwise list next batch')
    parser.add_argument('--limit',type=int,default=8)
    parser.add_argument('--finalize-reviewed',action='store_true',help='Delete only downloads with explicit accepted review receipts and valid derivatives')
    args=parser.parse_args()
    plan=json.loads((ROOT/'research/dictionary-expansion-plan.json').read_text('utf8'))
    STAGE.mkdir(parents=True,exist_ok=True)
    if args.finalize_reviewed:
        deleted=[]
        for receipt in STAGE.glob('*/receipt.json'):
            row=json.loads(receipt.read_text('utf8'));review=receipt.parent/'review.json';video=receipt.parent/'source.mp4'
            if not review.is_file() or not video.is_file():continue
            decision=json.loads(review.read_text('utf8'))
            if decision.get('accepted') is not True or decision.get('source_sha256')!=row.get('source_sha256'):continue
            if not row.get('extraction_complete') or not (receipt.parent/'source-timeline.jpg').is_file() or not (receipt.parent/'motion.json').is_file():raise ValueError('Review derivatives missing')
            if hashlib.sha256(video.read_bytes()).hexdigest()!=row['source_sha256']:raise ValueError('Source changed before deletion')
            if not video.resolve().is_relative_to(STAGE.resolve()):raise ValueError('Temporary path escaped staging root')
            size=video.stat().st_size;video.unlink();row.update(source_deleted=True,deleted_bytes=size);write(receipt,row);deleted.append({'id':row['id'],'bytes':size})
        print(json.dumps({'deleted':deleted,'scope':'Only reviewed source.mp4 files under explicit staging root.'}));return
    pending=[c for c in plan['candidates'] if not (STAGE/c['source_id']/'receipt.json').is_file()]
    batch=pending[:max(1,min(args.limit,16))]
    if not args.extract:print(json.dumps({'pending':len(pending),'next_batch':batch},ensure_ascii=False));return
    from motion_extract import extract_clip
    from build_reference_bank import build_word
    failures=0
    for candidate in batch:
        folder=STAGE/candidate['source_id'];folder.mkdir(parents=True,exist_ok=True)
        video=folder/'source.mp4';record={**candidate,'downloaded_at':datetime.now(timezone.utc).isoformat(),'extraction_complete':False,'source_deleted':False,'accepted':False}
        try:
            request=urllib.request.Request(candidate['url'],headers={'User-Agent':'VSL-Clinic-Reference-Review/0.7'})
            if not video.exists():
                with urllib.request.urlopen(request,timeout=40) as response:payload=response.read(30*1024*1024+1)
                if len(payload)>30*1024*1024 or b'ftyp' not in payload[:64]:raise ValueError('Not a bounded MP4')
                video.write_bytes(payload)
            record['source_sha256']=hashlib.sha256(video.read_bytes()).hexdigest()
            record['video']=source_sheet(video,folder/'source-timeline.jpg',candidate['label'])
            source={'video_id':candidate['id'],'signer_id':'qipedc-unknown-'+candidate['source_id'],'path':str(video),'sha256':record['source_sha256'],'url':candidate['url']}
            cache=extract_clip(source)
            with np.load(cache,allow_pickle=False) as arrays:
                visible=np.flatnonzero(np.max(arrays['confidence'][:,[33,54]],axis=1)>.5);times=arrays['time_ms']
                if len(visible)<8:raise ValueError('Insufficient observed hands')
                source['source_window_ms']=[max(0,float(times[visible[0]])-350),min(float(times[-1]),float(times[visible[-1]])+350)]
            word={**candidate,'source_kind':'qipedc-single','references':[source]}
            motion=build_word(word,folder)
            generated=folder/(candidate['id']+'.json');generated.replace(folder/'motion.json')
            record.update(extraction_complete=True,cache=str(cache),motion=motion,source=source,review_status='Candidate only: verify one front-facing take, handshape, contact, timing and meaning before promotion.')
            failures=0
        except Exception as error:
            record['error']=f'{type(error).__name__}: {error}';failures+=1
        write(folder/'receipt.json',record);print(json.dumps({'id':candidate['id'],'extracted':record['extraction_complete'],'error':record.get('error')},ensure_ascii=False),flush=True)
        if failures>=3:print('Stopping after three consecutive source failures; app unchanged.',flush=True);break

if __name__=='__main__':main()
