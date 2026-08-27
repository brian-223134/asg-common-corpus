"""ScienceLakeClient — one set of view names (openalex.works, ...) over either
the remote HF parquet files (hf://) or the local selective mirror.
Remote mode is for `doctor`/smoke only: works.parquet (135 GB) has no zone-map
pruning, so any remote filter is a full scan (~2 h at 18 MB/s, measured 2026-08-27).
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from common_corpus.config import UpstreamConfig

log = logging.getLogger("science_lake")

OPENALEX_TABLES = ["works", "works_topics", "works_locations", "topics", "subfields", "fields", "domains"]


class ScienceLakeClient:
    def __init__(self, cfg: UpstreamConfig, mode: str = "local", threads: int = 16):
        self.cfg = cfg
        self.mode = mode
        self.con = duckdb.connect()
        self.con.execute(f"SET threads={threads}")
        if mode == "remote":
            self.con.execute("INSTALL httpfs; LOAD httpfs; SET enable_object_cache=true;")
            base = f"hf://datasets/{cfg.repo_id}@{cfg.revision}/"
        elif mode == "local":
            base = str(cfg.mirror_path) + "/"
        else:
            raise ValueError(mode)
        self.base = base
        self.con.execute("CREATE SCHEMA IF NOT EXISTS openalex")
        for t in OPENALEX_TABLES:
            rel = f"openalex/{t}/{t}.parquet"
            if mode == "local" and not (cfg.mirror_path / rel).exists():
                continue
            self.con.execute(f"CREATE OR REPLACE VIEW openalex.{t} AS SELECT * FROM read_parquet('{base}{rel}')")

    def query(self, sql: str):
        return self.con.sql(sql)

    def materialize(self, sql: str, output_path: str | Path) -> None:
        self.con.execute(f"COPY ({sql}) TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
