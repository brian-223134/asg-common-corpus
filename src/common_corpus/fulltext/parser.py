"""LaTeX/PDF -> plain text. Versioned: cache entries record parser_version (spec §9)."""
from __future__ import annotations

import gzip
import io
import re
import subprocess
import tarfile
from pathlib import Path

PARSER_VERSION = "latex-v1"

_STRIP_ENVS = ("figure", "figure*", "table", "table*", "tikzpicture", "algorithm", "algorithmic", "thebibliography")


def _pick_main_tex(members: dict[str, bytes]) -> str | None:
    texs = {n: b for n, b in members.items() if n.lower().endswith(".tex")}
    for n, b in texs.items():
        if b"\\documentclass" in b and b"\\begin{document}" in b:
            return n
    for n, b in texs.items():
        if b"\\begin{document}" in b:
            return n
    return max(texs, key=lambda n: len(texs[n])) if texs else None


def _inline_inputs(text: str, members: dict[str, bytes], depth: int = 0) -> str:
    if depth >= 3:
        return text

    def repl(m: re.Match) -> str:
        name = m.group(2).strip()
        for cand in (name, name + ".tex"):
            if cand in members:
                return _inline_inputs(members[cand].decode("utf-8", "replace"), members, depth + 1)
        return ""

    return re.sub(r"\\(input|include)\{([^}]+)\}", repl, text)


def latex_to_text(source: str) -> str:
    s = re.sub(r"(?<!\\)%.*", "", source)                       # comments
    m = re.search(r"\\begin\{document\}(.*)\\end\{document\}", s, re.DOTALL)
    if m:
        s = m.group(1)
    for env in _STRIP_ENVS:
        s = re.sub(rf"\\begin\{{{re.escape(env)}\}}.*?\\end\{{{re.escape(env)}\}}", "", s, flags=re.DOTALL)
    s = re.sub(r"\\(sub)*section\*?\{([^}]*)\}", lambda m: "\n\n" + "#" * (2 + (m.group(1) or "").count("sub")) + " " + m.group(2) + "\n", s)
    s = re.sub(r"\\(title|abstract)\{([^}]*)\}", r"\2", s)
    s = re.sub(r"\\cite[tp]?\*?(\[[^]]*\])?\{[^}]*\}", "[CITATION]", s)
    s = re.sub(r"\\(ref|eqref|autoref|cref|Cref)\{[^}]*\}", "[REF]", s)
    s = re.sub(r"\\(label|bibliography|bibliographystyle|usepackage|documentclass|includegraphics)(\[[^]]*\])?\{[^}]*\}", "", s)
    s = re.sub(r"\\(textbf|textit|emph|texttt|textsc|mbox|text)\{([^{}]*)\}", r"\2", s)
    s = re.sub(r"\\begin\{(abstract|itemize|enumerate|description|quote)\}", "", s)
    s = re.sub(r"\\end\{(abstract|itemize|enumerate|description|quote)\}", "", s)
    s = re.sub(r"\\item\b", "\n- ", s)
    s = re.sub(r"\\(newline|par|noindent|centering|small|large|Large|maketitle|clearpage|newpage|hline|toprule|midrule|bottomrule)\b", "", s)
    s = re.sub(r"\\\\(\[[^]]*\])?", "\n", s)
    s = re.sub(r"\\[a-zA-Z]+\*?(\[[^]]*\])?", " ", s)           # remaining commands
    s = s.replace("~", " ").replace("{", "").replace("}", "")
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def parse_eprint(blob: bytes) -> tuple[str, str]:
    """arXiv e-print bytes -> (text, format). Formats: latex-tar, latex-single, pdf."""
    if blob[:4] == b"%PDF":
        return _pdf_to_text(blob), "pdf"
    try:
        raw = gzip.decompress(blob)
    except OSError:
        raise ValueError("unrecognized e-print payload (not gzip/pdf)")
    if raw[:4] == b"%PDF":
        return _pdf_to_text(raw), "pdf"
    try:
        with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
            members = {m.name: tf.extractfile(m).read() for m in tf.getmembers() if m.isfile() and m.size < 20_000_000}
        main = _pick_main_tex(members)
        if main is None:
            raise ValueError("no .tex file in e-print tarball")
        text = _inline_inputs(members[main].decode("utf-8", "replace"), members)
        return latex_to_text(text), "latex-tar"
    except tarfile.TarError:
        return latex_to_text(raw.decode("utf-8", "replace")), "latex-single"


def _pdf_to_text(pdf: bytes) -> str:
    p = subprocess.run(["pdftotext", "-enc", "UTF-8", "-", "-"], input=pdf, capture_output=True)
    if p.returncode != 0:
        raise ValueError(f"pdftotext failed: {p.stderr[:200]!r}")
    return p.stdout.decode("utf-8", "replace").strip()
