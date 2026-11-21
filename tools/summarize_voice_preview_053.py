"""Describe real fixture outcomes, including spoken uncertain errors."""
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT.parent / 'Organization/MultimodalIntegration_2026-11-09'
OUT = ROOT.parent / 'Organization/VoicePreviewCPU_2026-11-10'


def stats(values):
    values = sorted(values)
    if not values:
        return dict(n=0)
    return dict(n=len(values), p50=statistics.median(values),
                p95=values[min(len(values)-1, round((len(values)-1)*.95))],
                min=values[0], max=values[-1])


def summarize(folder):
    path = QA / folder / 'REPORT.json'
    if not path.is_file():
        return dict(evidence=str(path), available=False)
    report = json.loads(path.read_text('utf8'))
    trials = report.get('trials', [])
    rows, paint, audio, receive_audio, inference = [], [], [], [], []
    for trial in trials:
        word = trial['word']
        timing = word['metrics']['timing']
        original_audio = next((e for e in trial.get('voice', []) if e['type']=='playing'
            and e['message_id']==word['id'] and e['text']==word['text']), None)
        correct = word['predictions'][0]['class_id'] == trial['expected']
        reasons = word['recognition']['policy']['reasons']
        scores = [p['score'] for p in word['predictions'][:2]]
        old_clear = (not [r for r in reasons if r != 'ambiguous_closed_set_prediction']
                     and scores[0] >= .80 and scores[0]-scores[1] >= .25)
        rows.append(dict(clip=trial['fixture'].get('clip_id',trial['expected']),expected=trial['expected'],
            predicted=word['predictions'][0]['class_id'],correct=correct,
            yellow=word['uncertain'],spoken=bool(original_audio),old_threshold_clear=old_clear,
            new_threshold_clear=not word['uncertain'],score=scores[0],margin=scores[0]-scores[1],reasons=reasons))
        anchor = timing['backend_received_epoch_ms']
        arrival = timing['last_active_capture_to_result_ms'] + timing['worker_to_backend_ms']
        if trial.get('paint'):
            paint.append(arrival+trial['paint'][0]['painted_at_ms']-anchor)
        if original_audio:
            audio.append(arrival+original_audio['recorded_at_ms']-anchor)
            receive_audio.append(original_audio['recorded_at_ms']-anchor)
        inference.append(timing['inference_wall_ms'])
    voice = report.get('perSignVoice', {})
    return dict(evidence=str(path),available=True,passed=report['passed'],checks=report['checks'],
        device=report.get('worker',{}).get('worker',{}),renderer=report.get('graphics'),
        clips=len(rows),green=sum(not r['yellow'] for r in rows),yellow=sum(r['yellow'] for r in rows),
        top1_correct=sum(r['correct'] for r in rows),wrong_green=sum(not r['correct'] and not r['yellow'] for r in rows),
        spoken_original=sum(r['spoken'] for r in rows),wrong_spoken=sum(r['spoken'] and not r['correct'] for r in rows),
        changed_by_threshold=[r for r in rows if r['old_threshold_clear']!=r['new_threshold_clear']],
        rows=rows,preview=report.get('preview'),
        avatar_voice_offsets_ms=[e['timeline_ms']-c['start_ms'] for e,c in zip(voice.get('events',[]),voice.get('cues',[]))],
        latency=dict(last_active_frame_to_paint=stats(paint),last_active_frame_to_voice=stats(audio),
            backend_received_to_voice=stats(receive_audio),inference=stats(inference)),
        worker_memory=report.get('workerMemory'),shutdown_ms=report.get('shutdownMs'),error=report.get('error'))


def main():
    report = dict(version='0.5.3',scope='Repeated fixed fixtures with original VSL100 mouth pixels. Software clocks/audio events; not acoustic/display-photon latency or independent clinical accuracy.',
        source=summarize('source-ui-final-voice-preview-053-source3'),
        portable=summarize('packaged-ui-12-voice-preview-053-exe2'),
        cpu=summarize('packaged-ui-12-voice-preview-053-cpu1'),
        installed=summarize('packaged-ui-12-voice-preview-053-installed1'),
        owner_decisions=dict(read_yellow_immediately=True,beep_before_yellow=True,doctor_top_candidates=3,green='clear_or_confirmed',yellow='uncertain',
            thresholds=dict(score=.75,margin=.20),baseline_preserved=True),
        limits=['Yellow wrong words are spoken too; readout does not equal confirmation.',
            'The same fixtures are reused; scheduling/load changes observed frames and predictions.',
            'CPU inference test does not imply that WebGL rendering avoids the GPU.',
            'No camera/person/room noise or Raspberry Pi/Jetson test in this phase.'])
    for name in ['CPU_DIRECT_LOAD.json','CPU_INITIAL_COMPARISON.json','CPU_PACKAGE-beep.json']:
        path=OUT/name
        if path.is_file():
            report[name]=json.loads(path.read_text('utf8'))
    (OUT/'SUMMARY.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps({name:{k:v for k,v in report[name].items() if k in ['available','passed','clips','green','yellow','top1_correct','wrong_green','spoken_original','wrong_spoken','preview','latency']}
        for name in ['source','portable','cpu','installed']},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
