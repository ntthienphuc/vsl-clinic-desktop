"""Stage exactly 96 local motion additions, preserving the 104-word baseline.

Three signer references per new word, source hashes, no raw-video copies and
no recognizer training/label changes. Promote only after staging succeeds.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib
import json
from pathlib import Path
import sys
import subprocess

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'research/cache/clinic200'

def read(p):return json.loads(p.read_text('utf8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2),'utf8');tmp.replace(p)

def extract_batch(rows):
    from motion_extract import extract_clip
    failures=[]
    for row in rows:
        try:extract_clip(row)
        except Exception as error:failures.append({'id':row['video_id'],'error':str(error)})
    return failures

def run_batch(path):
    completed=subprocess.run([sys.executable,'-u','-X','utf8',str(Path(__file__).resolve()),'--extract-batch',str(path)],capture_output=True,text=True,encoding='utf8',errors='replace')
    if completed.returncode:
        raise RuntimeError(f'Extraction batch {path.name}: exit {completed.returncode}: '+completed.stderr[-2000:])
    return read(path.with_suffix('.result.json'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--promote',action='store_true');parser.add_argument('--workers',type=int,default=2);parser.add_argument('--extract-batch',type=Path);args=parser.parse_args()
    if args.extract_batch:
        write(args.extract_batch.with_suffix('.result.json'),extract_batch(read(args.extract_batch)))
        return
    manifest=read(ROOT/'research/source-manifest.json');vocab=read(ROOT/'assets/vocabulary.json');bank=read(ROOT/'assets/motions/manifest.json')
    if len(vocab) not in (104,200):raise ValueError('Unexpected current bank')
    if len(vocab)==200:print('200-word vocabulary already promoted; existing bytes retained.');return
    metadata_path=Path(manifest['metadata_path']);metadata=read(metadata_path)
    if digest(metadata_path)!=manifest['metadata_sha256']:raise ValueError('Source metadata changed')
    catalogue=read(ROOT/'assets/catalog.json')['words'];by_label={w['label']:w for w in catalogue};existing={w['label'] for w in vocab}
    selection=read(ROOT/'research/clinic200-selection.json');words=[]
    for group,labels in selection.items():
        for label in labels:
            if label in existing:raise ValueError('Duplicate current label '+label)
            item=by_label[label];sources=[r for r in metadata if r['gloss']==label and r['video_id']!=item['video_id']]
            references=[];signers=set()
            for r in sorted(sources,key=lambda r:(abs(r['length']-2.8),r['video_id'])):
                p=metadata_path.parent/'All_cam1'/(r['video_id']+'.mp4')
                if r['signer_id'] in signers or not p.is_file():continue
                references.append({**r,'path':str(p),'sha256':digest(p)});signers.add(r['signer_id'])
                if len(references)==3:break
            if len(references)!=3:raise ValueError('Need three signer references: '+label)
            words.append({'id':str(item['model_id']),'label':label,'model_id':item['model_id'],'category':group,'demo':None,'source_kind':'local-consensus','minimum_reference_signers':3,'references':references})
    if len(words)!=96:raise ValueError(f'Expected 96 new words, got {len(words)}')
    prior_path=STAGE/'source-manifest.json'
    if prior_path.exists():
        previous={w['id']:w for w in read(prior_path)['words']}
        for word in words:
            known={r['video_id'] for r in word['references']}
            for ref in previous.get(word['id'],{}).get('references',[]):
                if ref['video_id'] not in known and Path(ref['path']).is_file() and digest(Path(ref['path']))==ref['sha256']:
                    word['references'].append(ref);known.add(ref['video_id'])
    STAGE.mkdir(parents=True,exist_ok=True);write(STAGE/'source-manifest.json',{'schema':'clinic200-staged-sources-v1','words':words,'original_vocabulary_sha256':digest(ROOT/'assets/vocabulary.json')})
    if not args.promote:
        tasks=[r for word in words for r in word['references']]
        failures=[]
        # Fresh bounded subprocesses avoid both native resource accumulation and
        # Python 3.11's recycling ProcessPoolExecutor stalling with queued tasks.
        batches=[]
        for start in range(0,len(tasks),6):
            path=STAGE/'batches'/f'{start//6:03}.json';write(path,tasks[start:start+6]);batches.append(path)
        with ThreadPoolExecutor(max_workers=max(1,min(args.workers,2))) as pool:
            jobs={pool.submit(run_batch,p):p for p in batches}
            for i,job in enumerate(as_completed(jobs),1):
                try:failures.extend(job.result());print(f'EXTRACT BATCH {i}/{len(batches)} {jobs[job].name}',flush=True)
                except Exception as error:failures.append({'batch':jobs[job].name,'error':str(error)});print(f'ERROR {error}',flush=True)
        write(STAGE/'extraction.json',{'failures':failures,'references':len(tasks)})
        if failures:raise ValueError('Extraction failures: '+str(len(failures)))
        from build_reference_bank import build_word,load_sequence
        output=STAGE/'motions';output.mkdir(exist_ok=True);entries=[]
        for i,word in enumerate(words,1):
            usable=set()
            for ref in word['references']:
                try:load_sequence(ref);usable.add(ref['signer_id'])
                except (ValueError,FileNotFoundError):pass
            if len(usable)<3:
                known={r['video_id'] for r in word['references']}
                candidates=sorted((r for r in metadata if r['gloss']==word['label'] and r['video_id'] not in known),key=lambda r:(abs(r['length']-2.8),r['video_id']))
                for candidate in candidates:
                    if candidate['signer_id'] in usable:continue
                    path=metadata_path.parent/'All_cam1'/(candidate['video_id']+'.mp4')
                    if not path.is_file():continue
                    ref={**candidate,'path':str(path),'sha256':digest(path)}
                    batch=STAGE/'batches'/('fallback-'+ref['video_id']+'.json');write(batch,[ref])
                    if run_batch(batch):continue
                    word['references'].append(ref)
                    try:load_sequence(ref);usable.add(ref['signer_id'])
                    except ValueError:pass
                    if len(usable)>=3:break
                write(STAGE/'source-manifest.json',{'schema':'clinic200-staged-sources-v1','words':words,'original_vocabulary_sha256':digest(ROOT/'assets/vocabulary.json')})
            entry=build_word(word,output);entries.append(entry);write(STAGE/'manifest.json',{'entries':entries})
            print(f'BANK {i}/96 {word["label"]}',flush=True)
        return
    staged=read(STAGE/'manifest.json')['entries']
    if len(staged)!=96 or {e['id'] for e in staged}!={w['id'] for w in words}:raise ValueError('Staged bank incomplete')
    for entry in staged:
        original=STAGE/'motions'/(entry['id']+'.json');target=ROOT/'assets/motions'/original.name
        if digest(original)!=entry['sha256']:raise ValueError('Staged motion changed')
        if target.exists() and digest(target)!=entry['sha256']:raise ValueError('Refuse overwrite original motion')
    for entry in staged:(ROOT/'assets/motions'/(entry['id']+'.json')).write_bytes((STAGE/'motions'/(entry['id']+'.json')).read_bytes())
    vocab.extend({k:v for k,v in w.items() if k!='references'} for w in words);manifest['words'].extend(words);bank['entries'].extend(staged)
    write(ROOT/'assets/vocabulary.json',vocab);write(ROOT/'research/source-manifest.json',manifest);write(ROOT/'assets/motions/manifest.json',bank)
    print('Promoted 200 words; original 104 motion JSON files were not modified.')

if __name__=='__main__':main()
