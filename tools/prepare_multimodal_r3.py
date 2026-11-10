"""Stage the best existing VSL100 R3 fusion without changing research artifacts.

The model family is selected from the frozen 18-cell research ranking.
Fold01/seed17 stays fixed, as in the previous Clinic deployment.
"""
from pathlib import Path
import json
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from multimodal.runtime import sha256

SUP = Path(r"E:\Paper\MultiModel Paper\Multimodal_Expanded_20261105\supplemental")
RESEARCH = Path(r"E:\Paper\MultiModel Paper\VSL100_R3_20261106")
QA = ROOT.parent / "Organization/MultimodalIntegration_2026-11-09/fusion_explore"
DEST = ROOT / "assets/multimodal100"
RUN = "primary__r3_loso_01__slgcn_replication_fp32__avhubert_replication_fp32__cross_attention__s17"


def stage(source, relative):
    target = DEST / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert sha256(source) == sha256(target), str(target)
    elif source.stat().st_size > 10_000_000:
        os.link(source, target)
    else:
        shutil.copy2(source, target)
    return dict(path=relative, sha256=sha256(target), bytes=target.stat().st_size,
                source=str(source))


def main():
    previous = json.loads((QA/"before-r3/assets/multimodal100/DEPLOYMENT.json").read_text("utf8"))
    records = [r for r in previous["files"] if r["path"] != "models/MODEL_MANIFEST.json"]
    for folder in ["assets/slgcn", "assets/avhubert", "vendor/slgcn"]:
        for file in (SUP/folder).rglob("*"):
            if file.is_file() and "__pycache__" not in file.parts:
                records.append(stage(file, "r3/"+file.relative_to(SUP).as_posix()))
    for relative in ["code/sign_backbones.py", "vendor/pose_transforms.py"]:
        records.append(stage(SUP/relative, "r3/"+relative))
    source = SUP/"vendor/avhubert_source"
    files = ["LICENSE", "avhubert/hubert.py", "avhubert/resnet.py", "fairseq/LICENSE",
             "fairseq/fairseq/incremental_decoding_utils.py", "fairseq/fairseq/utils.py",
             "fairseq/fairseq/models/wav2vec/wav2vec2.py"]
    files += ["fairseq/fairseq/modules/"+n+".py" for n in [
        "gelu","quant_noise","fairseq_dropout","grad_multiply","same_pad","transpose_last",
        "multihead_attention","transformer_sentence_encoder"]]
    for relative in files:
        records.append(stage(source/relative, "r3/vendor/avhubert_source/"+relative))
    deps = SUP/"vendor/runtime_linux_deps"
    for folder in [p for p in deps.iterdir() if p.name == "pose_format" or p.name.startswith("pose_format-")]:
        for file in folder.rglob("*"):
            if file.is_file() and "__pycache__" not in file.parts:
                records.append(stage(file, "r3/deps/"+file.relative_to(deps).as_posix()))
    records.append(stage(QA/"avhubert_preset.json", "r3/avhubert_preset.json"))
    proof = json.loads((RESEARCH/"results"/RUN/"ARTIFACT_HASHES.json").read_text("utf8"))
    for name in ["best.pt", "config_and_provenance.json"]:
        assert sha256(RESEARCH/"results"/RUN/name) == proof[name]
        records.append(stage(RESEARCH/"results"/RUN/name, "r3/head/"+name))
    records.append(stage(RESEARCH/"results"/RUN/"ARTIFACT_HASHES.json", "r3/head/ARTIFACT_HASHES.json"))
    label_hash = sha256(DEST/"models/classes.json")
    assert label_hash == "498208e0034ac32154937f261511b2c932fda9766526a53566421a1daad2ba9a"
    foundations = {
        "slgcn.safetensors": "r3/assets/slgcn/model.safetensors",
        "avhubert_encoder.pt": "r3/assets/avhubert/encoder_state.pt"}
    contract = "vsl100-r3-slgcn-avhubert-xattn-f01-s17-clinic-v1"
    manifest = dict(contract=contract, profile="slgcn-avhubert", fold="r3_loso_01", seed=17,
        test_signer="Huy", validation_signer="Học", label_sha256=label_hash, label_count=100,
        boundary_contract="clinic-r3-elbow140-context500-400-v1; unchanged decision; observed frames only",
        selection_rule="Highest mean macro-F1 in the existing VSL100 R3 6-fold x 3-seed leaderboard. Fixed fold01/seed17 retained; no checkpoint search or training on Clinic fixtures.",
        heads=dict(fusion=dict(run_id=RUN, checkpoint="r3/head/best.pt", sha256=proof["best.pt"],
                              config_sha256=proof["config_and_provenance.json"], source_manifest=proof)),
        foundations={name:dict(path=path, sha256=sha256(DEST/path), bytes=(DEST/path).stat().st_size)
                     for name,path in foundations.items()},
        feature_contract=dict(sign_dim=256, lip_dim=1024, sign_max_frames=150, lip_max_tokens=96,
                              precision="fp32_tf32_off", sign_device="same_as_mouth",
                              mouth="full 25fps gray96 center88 (x/255-.421)/.165 before uniform feature sampling"),
        files=[r for r in records if r["path"].startswith("r3/") or r["path"]=="models/classes.json"])
    path = DEST/"models/MODEL_MANIFEST.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf8")
    records.append(dict(path="models/MODEL_MANIFEST.json", sha256=sha256(path), bytes=path.stat().st_size))
    # Unique identity per staged file. Previous source remains available for provenance.
    unique = {r["path"]:r for r in records}
    deployment = dict(previous, contract=contract, profile="slgcn-avhubert",
        source_manifest_sha256=sha256(path), foundations=foundations, files=list(unique.values()),
        previous_contract=previous["contract"])
    (DEST/"DEPLOYMENT.json").write_text(json.dumps(deployment, ensure_ascii=False, indent=2), "utf8")
    print(json.dumps(dict(contract=contract, files=len(unique), checkpoint=proof["best.pt"])))


if __name__ == "__main__":
    main()
