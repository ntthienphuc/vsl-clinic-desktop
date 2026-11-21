import json
from pathlib import Path
from backend.language_assist import LanguageAssist, candidates_for, semantic_candidates
from backend.text_to_sign import TextPlanner

ASSETS=Path(__file__).resolve().parents[1]/'assets'
def planner():
    read=lambda n:json.loads((ASSETS/n).read_text('utf8'))
    return TextPlanner(read('vocabulary.json'),read('phrases.json'),read('semantic_bank.json'))

def test_zero_lexical_overlap_still_reaches_semantic_retrieval():
    entries=[{'id':'thanks','text':'Cảm ơn'},{'id':'hello','text':'Xin chào'}]
    assert not candidates_for('Xin kiên nhẫn.',entries)
    assert len(semantic_candidates('Xin kiên nhẫn.',entries))==2

def test_known_rephrasing_is_never_marked_supported_or_auto_sent():
    p=planner();h=LanguageAssist(ASSETS,p)
    try:
        r=h.resolve('Tạm ngưng.')
        assert not r['supported']
        assert r['suggestions'][0]['text']=='Dừng lại'
        assert r['text']=='Tạm ngưng.'
    finally:h.close()

def test_unrelated_model_choice_is_rejected(monkeypatch):
    p=planner();h=LanguageAssist(ASSETS,p)
    monkeypatch.setattr(LanguageAssist,'available',property(lambda self:True))
    monkeypatch.setattr(h,'_start',lambda:None)
    def respond(route,payload,**kwargs):
        if payload['response_format']['json_schema']['name']=='meaning_check':
            return {'choices':[{'message':{'content':'{"equivalent":false}'}}]}
        return {'choices':[{'message':{'content':'{"id":"0"}'}}]}
    monkeypatch.setattr(h,'_request',respond)
    try:
        assert not h.suggest('Xin kiên nhẫn.')['suggestions']
    finally:h.close()
