"""Dropped observations cannot be promoted by an overconfident closed-set score."""
from copy import deepcopy
import pytest
from multimodal.sampling import observation_continuity
from multimodal.policy import decide, recognition_event

QUALITY = dict(sign_valid=True, mouth_valid=True, hand_coverage=.9,
               single_face_fraction=.9, input_fps=25, max_capture_gap_ms=50,
               model_cadence_observed=True)
BOUNDARY = dict(reason="arms_returned_to_neutral")


def prediction():
    return dict(status="ok", logits=[2., 0.], top_k=[
        dict(index=0,class_id="W021",gloss="Quen",score=.99),
        dict(index=1,class_id="W082",gloss="Nhà vệ sinh",score=.005)])


@pytest.mark.parametrize('sequences', [[1,2,4,5], [21,22,24], [1,1,2], [2,1], [None,2], []])
def test_missing_or_invalid_samples_stay_review_even_at_high_score(sequences):
    result=prediction(); before=deepcopy(result)
    quality={**QUALITY,**observation_continuity(sequences)}
    policy=decide(result,quality,BOUNDARY,require_continuity=True)
    assert not policy['committed'] and 'interrupted_temporal_sampling' in policy['reasons']
    assert result==before


def test_complete_word_after_earlier_overload_can_be_green():
    quality={**QUALITY,**observation_continuity([71,72,73,74])}
    result=prediction();result['top_k'][0]['score']=.71
    assert decide(result,quality,BOUNDARY,require_continuity=True)['committed']
    result['top_k'][0]['score']=.69
    assert not decide(result,quality,BOUNDARY,require_continuity=True)['committed']
    result['top_k'][0]['score']=.99
    assert not decide(result,{**quality,'mouth_valid':False},BOUNDARY,require_continuity=True)['committed']


def test_continuous_but_lower_rate_camera_is_not_certified():
    quality={**QUALITY,**observation_continuity([1,2,3,4]),
             'input_fps':20,'model_cadence_observed':False}
    policy=decide(prediction(),quality,BOUNDARY,require_continuity=True)
    assert not policy['committed'] and 'insufficient_model_cadence' in policy['reasons']


def test_r3_still_emits_original_word_for_immediate_uncertain_readout():
    result=prediction()
    mapping=[dict(class_id=p['class_id'],original_gloss=p['gloss'],display_text=p['gloss'],
                  class_index=p['index'],canonical_concept_id='mm100:'+p['class_id'],
                  legacy_label_candidate=None,voice_key=p['class_id']) for p in result['top_k']]
    event=recognition_event(result,{**QUALITY,**observation_continuity([1,2,4])},BOUNDARY,mapping,
        dict(contract='vsl100-r3-fixture',manifest_sha256='fixture',fusion_sha256='fixture'),
        'fixture:1',dict(inference_wall_ms=1))
    assert event['type']=='recognition' and not event['policy']['committed']
    assert event['predictions'][0]['class_id']=='W021'
    assert event['raw_logits']==result['logits']
