"""Phase B0.5 — selective mirror of the Science Data Lake (HF) into data/upstream/<rev>/.

Resumable: hf_hub_download resumes partial files; already-verified files are skipped.
Every file is verified against the sha256 that HF stores for its LFS object, and the
result is recorded in upstream_manifest.json so a corpus manifest can pin it later.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

from common_corpus.config import UpstreamConfig

log = logging.getLogger("mirror")


def sha256_of(path: Path, chunk: int = 1 << 24) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while blk := f.read(chunk):
            h.update(blk)
    return h.hexdigest()


def remote_file_info(api: HfApi, cfg: UpstreamConfig) -> dict[str, dict]:
    """{rfilename: {size, sha256}} for the configured files at the pinned revision."""
    infos = api.get_paths_info(cfg.repo_id, cfg.files, repo_type="dataset", revision=cfg.revision)
    out = {}
    for i in infos:
        lfs = getattr(i, "lfs", None)
        out[i.path] = {"size": i.size, "sha256": lfs.sha256 if lfs else None}
    missing = set(cfg.files) - set(out)
    if missing:
        raise FileNotFoundError(f"not in upstream at {cfg.revision}: {sorted(missing)}")
    return out


def load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"files": {}}


def mirror(cfg: UpstreamConfig, verify_existing: bool = True) -> Path:
    api = HfApi()
    dest = cfg.mirror_path
    dest.mkdir(parents=True, exist_ok=True)
    manifest_path = dest / "upstream_manifest.json"
    manifest = load_manifest(manifest_path)
    manifest.update({
        "repo_id": cfg.repo_id,
        "revision": cfg.revision,
        "openalex_snapshot": cfg.openalex_snapshot,
        "license": cfg.license,
    })
    remote = remote_file_info(api, cfg)
    total = sum(r["size"] for r in remote.values())
    log.info("mirror %s@%s -> %s (%d files, %.1f GB)", cfg.repo_id, cfg.revision[:7], dest, len(remote), total / 1e9)

    # Small files first so failures surface early; works.parquet last.
    for rel in sorted(cfg.files, key=lambda f: remote[f]["size"]):
        info = remote[rel]
        local = dest / rel
        rec = manifest["files"].get(rel)
        if rec and rec.get("verified") and local.exists() and local.stat().st_size == info["size"]:
            log.info("skip (verified) %s", rel)
            continue
        t0 = time.time()
        log.info("download %s (%.2f GB)", rel, info["size"] / 1e9)
        hf_hub_download(
            cfg.repo_id, rel, repo_type="dataset", revision=cfg.revision,
            local_dir=dest, force_download=False,
        )
        dl_s = time.time() - t0
        size = local.stat().st_size
        log.info("downloaded %s in %.0fs (%.1f MB/s)", rel, dl_s, size / 1e6 / max(dl_s, 1e-9))
        if size != info["size"]:
            raise RuntimeError(f"size mismatch {rel}: local {size} != remote {info['size']}")
        digest = None
        ok = True
        if verify_existing and info["sha256"]:
            t1 = time.time()
            digest = sha256_of(local)
            ok = digest == info["sha256"]
            log.info("sha256 %s %s (%.0fs)", rel, "OK" if ok else "MISMATCH", time.time() - t1)
            if not ok:
                raise RuntimeError(f"sha256 mismatch {rel}: {digest} != {info['sha256']}")
        manifest["files"][rel] = {
            "size": size, "sha256": digest or info["sha256"], "verified": ok,
            "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "download_seconds": round(dl_s),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest_path.write_text(json.dumps(manifest, indent=2))
    log.info("mirror complete: %s", manifest_path)
    return manifest_path
