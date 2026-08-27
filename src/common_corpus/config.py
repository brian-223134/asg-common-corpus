from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class UpstreamConfig(BaseModel):
    repo_id: str
    revision: str
    openalex_snapshot: str
    license: str
    mirror_dir: str
    files: list[str]

    @property
    def mirror_path(self) -> Path:
        p = Path(self.mirror_dir)
        return p if p.is_absolute() else PROJECT_ROOT / p


def load_upstream(path: str | Path | None = None) -> UpstreamConfig:
    path = Path(path) if path else PROJECT_ROOT / "config" / "upstream.yaml"
    with open(path) as f:
        return UpstreamConfig(**yaml.safe_load(f))
