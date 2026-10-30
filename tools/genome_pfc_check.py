#!/usr/bin/env python3
"""
genome_pfc_check — o teste de regressao de um PFC tem de EXISTIR, inclusive
quando ele mora em outro repositorio.

A FIT-014 diz: PFC so conta com teste de regressao que existe, e o juiz confere
o nome dentro do arquivo. Isso funciona enquanto o teste mora no proprio
genoma. A partir do momento em que um PFC nasce de um PROCESSO REAL — uma
planta, uma declaracao, uma exigencia —, o teste que o sustenta mora no
monolito que implementa a regra, e o juiz nao tem esse arquivo.

A solucao e a mesma da invalidacao de prova (genome_surface_check): a
conferencia acontece ONDE O ARQUIVO ESTA. Esta ferramenta roda na CI do
monolito, le o genoma PUBLICO, pega os PFC cujo ``regression_tests[].repo`` e
este repositorio, e falha aqui se o arquivo sumiu ou se o teste nao esta mais
nele:

    FC-XXX aponta test_... em backend/tests/..., e esse teste nao esta la —
    o PFC deixou de ter prova executavel

Sem token, e sem ninguem escrever no repositorio de ninguem.

Uso, na CI do monolito:
    python genome_pfc_check.py --repo <nome-no-genoma> [--root .] [--pfc <url ou arquivo>]

Saida 0: todos os testes de regressao deste repo existem.
Saida 1: algum sumiu, ou mudou de nome.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

import yaml

GENOME_PFC_URL = ("https://raw.githubusercontent.com/laverssiera/liceu-genome/"
                  "main/genome/11-pfc.yaml")


def load_pfc(source: str) -> list[dict]:
    if source.startswith("http://") or source.startswith("https://"):
        with urllib.request.urlopen(source, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    else:
        raw = Path(source).read_text(encoding="utf-8")
    return [n for n in (yaml.safe_load(raw) or []) if n.get("kind") == "pfc"]


def test_presente(arquivo: Path, nome: str) -> bool:
    """O teste existe no arquivo? Aceita `def nome(` e o metodo dentro de
    classe; nao aceita o nome aparecendo so num comentario ou numa string."""
    texto = arquivo.read_text(encoding="utf-8", errors="replace")
    return re.search(rf"^\s*(?:async\s+)?def\s+{re.escape(nome)}\s*\(", texto, re.M) is not None


def check(pfcs: list[dict], repo: str, root: Path) -> list[str]:
    problemas = []
    alvos = [(fc, t) for fc in pfcs
             for t in fc.get("regression_tests", []) if t.get("repo") == repo]
    if not alvos:
        print(f"nenhum PFC do genoma aponta teste em {repo!r} — nada a conferir")
        return problemas
    for fc, t in alvos:
        arquivo = root / t["file"]
        if not arquivo.is_file():
            problemas.append(
                f"{fc['id']}: o teste de regressao {t['file']!r} nao existe mais neste "
                f"repositorio. O PFC ficou sem prova executavel — restaure o teste, ou "
                f"retire o PFC do genoma (liceu-genome, genome/11-pfc.yaml).")
        elif not test_presente(arquivo, t["name"]):
            problemas.append(
                f"{fc['id']}: {t['name']!r} nao esta mais em {t['file']!r}.\n"
                f"    O PFC {fc.get('title', '')[:60]!r} afirma que este teste impede a falsa\n"
                f"    afirmacao. Se o teste mudou de nome, atualize o genoma; se foi removido,\n"
                f"    o PFC deixou de valer.")
        else:
            print(f"  [OK] {fc['id']} -> {t['file']}::{t['name']}")
    return problemas


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--repo", required=True, help="nome do repositorio como o genoma o chama")
    ap.add_argument("--root", default=".", help="raiz do checkout deste repositorio")
    ap.add_argument("--pfc", default=GENOME_PFC_URL)
    a = ap.parse_args(argv)
    problemas = check(load_pfc(a.pfc), a.repo, Path(a.root))
    if problemas:
        print("\nPFC SEM PROVA EXECUTAVEL\n")
        for p in problemas:
            print("  x", p)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
