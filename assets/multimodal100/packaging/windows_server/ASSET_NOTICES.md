# VSL Server 1.0.1 — local review build

This installer is prepared for private product review. It is not a cleared public
redistribution release and is not Authenticode signed.

The three ONNX models are local project artifacts. Their source checkpoints and
hashes are recorded in models/MODEL_PROVENANCE.md. That provenance is not evidence
of redistribution permission for the underlying training data, upstream model
code or weights. Owner review remains required before public distribution.

gloss.csv and dictionary_manifest.json contain the 400-class label/catalog
metadata. Metadata rights require the same owner review. No dictionary MP4,
training dataset, private pose logs or source checkpoint is included. Dictionary
entries can be browsed; video playback is unavailable until the operator installs
an authorized video pack in dictionary_videos.

Redis 5.0.14.1 Windows binary comes from the local installed tporadowski/redis
distribution. Its version and binary hash are included in bundle-manifest.json.
Project source: https://github.com/tporadowski/redis
The retained BSD license is redis/REDIS-COPYING.txt (retrieved from the project's
master/COPYING on 2026-10-12). This legacy Windows port is not current upstream
Redis. It binds only to loopback, disables disk persistence, and is stopped only
when owned by this launcher. An existing healthy loopback Redis is borrowed.

Python runtime and dependency notices are collected in third-party-notices.
Dependency versions are captured in dependency-versions.json. License collection
supports review; it does not assert that every redistribution obligation has been
cleared. A clean Windows VM and owner license/signing approval remain release gates.
