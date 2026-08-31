import gzip
import json

import pytest

from common_corpus.fulltext.parser import latex_to_text, parse_eprint
from common_corpus.fulltext.resolver import FullTextResolver
from common_corpus.fulltext.providers import RawFullText


LATEX = r"""
\documentclass{article}
\usepackage{amsmath}
% a comment line
\begin{document}
\title{My Paper}
\section{Intro\label{sec:intro}}
Hello \textbf{world}~\cite{smith2020} and \ref{sec:x}.
\begin{figure}should vanish\end{figure}
\begin{itemize}\item one \item two\end{itemize}
\end{document}
"""


def test_latex_to_text():
    t = latex_to_text(LATEX)
    assert "## Intro" in t and "Hello world" in t
    assert "[CITATION]" in t and "[REF]" in t
    assert "should vanish" not in t and "% a comment" not in t and "amsmath" not in t


def test_parse_eprint_single_gz():
    text, fmt = parse_eprint(gzip.compress(LATEX.encode()))
    assert fmt == "latex-single" and "Hello world" in text


class FakeProvider:
    name = "arxiv"
    calls = 0

    def fetch(self, arxiv_id, version=None):
        FakeProvider.calls += 1
        return RawFullText("arxiv", arxiv_id, "v2", gzip.compress(LATEX.replace("Hello", "pad " * 300 + "Hello").encode()))


def test_resolver_cache_hit_no_network(tmp_path):
    r = FullTextResolver(corpus_dir=tmp_path, cache_dir=tmp_path / "cache", provider=FakeProvider())
    d1 = r.resolve(arxiv_id="2401.00001")
    n = FakeProvider.calls
    d2 = r.resolve(arxiv_id="2401.00001")          # cache hit
    assert FakeProvider.calls == n
    assert d1.sha256 == d2.sha256 and d1.version == "v2"
    meta = json.loads((tmp_path / "cache/arxiv/2401.00001/metadata.json").read_text())
    assert meta["sha256"] == d1.sha256 and meta["parser_version"]


class FailingProvider:
    name = "arxiv"

    def fetch(self, arxiv_id, version=None):
        raise ValueError("boom")


def test_resolver_records_failure(tmp_path):
    r = FullTextResolver(corpus_dir=tmp_path, cache_dir=tmp_path / "cache", provider=FailingProvider())
    with pytest.raises(ValueError):
        r.resolve(arxiv_id="2401.00002")
    with pytest.raises(RuntimeError, match="previous failure"):   # 재시도는 명시적 삭제 후에만
        r.resolve(arxiv_id="2401.00002")
