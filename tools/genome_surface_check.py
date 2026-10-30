#!/usr/bin/env python3
"""
genome_surface_check — a invalidacao acontece ONDE A MUDANCA ACONTECE.

Roda na CI de CADA monolito, contra o genoma PUBLICO. Le as provas, filtra as
que cobrem arquivos DESTE repositorio (``mechanism.repo``), recalcula o hash da
superficie declarada e compara. Mudou -> a CI DO MONOLITO falha:

    este PR altera uma superficie provada por PRF-XXXX — registre uma prova
    nova no genoma (liceu-genome), com o hash atual

Por que aqui, e nao no juiz: o juiz roda no repositorio do genoma e nao tem os
arquivos dos monolitos. Ninguem precisa de token: o genoma e publico, cada
monolito le o genoma, e ninguem escreve no repositorio de ninguem. Foi o genoma
ser publico que tornou isto possivel.

E PREVENCAO, nao deteccao tardia: o PR que muda a superficie nao entra sem que a
prova nova exista. Quando alguem contorna (merge direto, prova vencida), o juiz
ainda deriva STALE pelo ``expires_at``.

Uso, na CI do monolito:
    python genome_surface_check.py --repo <nome-no-genoma> [--root .]
                                   [--proofs <url ou arquivo>]

Saida 0: nenhuma superficie deste repo divergiu.
Saida 1: divergencia (ou arquivo provado que sumiu).
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

import yaml

GENOME_PROOFS_URL = ("https://raw.githubusercontent.com/laverssiera/liceu-genome/"
                     "main/genome/07-proofs.yaml")


def surface_hash(root: Path, paths: list[str]) -> tuple[str, list[str]]:
    """Hash da superficie: caminho + conteudo de cada arquivo, em ordem.

    Fim de linha normalizado para LF: CRLF no checkout do Windows nao pode
    fazer a prova parecer invalida — a superficie e o conteudo, nao o checkout.
    """
    h = hashlib.sha256()
    faltando = []
    for rel in sorted(paths):
        f = root / rel
        if not f.is_file():
            faltando.append(rel)
            continue
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(f.read_bytes().replace(b"\r\n", b"\n"))
        h.update(b"\0")
    return h.hexdigest(), faltando


def load_proofs(source: str) -> list[dict]:
    if source.startswith("http://") or source.startswith("https://"):
        with urllib.request.urlopen(source, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    else:
        raw = Path(source).read_text(encoding="utf-8")
    return yaml.safe_load(raw) or []


def check(proofs: list[dict], repo: str, root: Path) -> list[str]:
    problemas = []
    # Prova SUPERSEDED nao e conferida. O esquema do genoma ja diz isso sobre o
    # campo `supersedes`: "a prova superseded fica no grafo (historia); so as
    # vigentes — as que nenhuma outra supersede — entram na derivacao". O juiz
    # respeitava; esta guarda nao, e cobrava para sempre uma superficie que o
    # grafo ja tinha aposentado.
    #
    # O estrago nao era so ruido. A unica forma de calar a guarda seria editar
    # o content_hash da prova velha — ou seja, reescrever a historia, que e
    # exatamente o que a supersessao existe para evitar. Duas ferramentas lendo
    # o mesmo grafo com regras diferentes sao duas verdades, e a segunda
    # envelhece calada.
    aposentadas = {pid for p in proofs for pid in (p.get("supersedes") or [])}
    cobre = [p for p in proofs
             if isinstance(p.get("mechanism"), dict) and p["mechanism"].get("repo") == repo
             and p["id"] not in aposentadas]
    if not cobre:
        print(f"nenhuma prova do genoma cobre superficie de {repo!r} — nada a conferir")
        return problemas
    for p in cobre:
        m = p["mechanism"]
        atual, faltando = surface_hash(root, list(m.get("paths") or []))
        for rel in faltando:
            problemas.append(
                f"{p['id']}: o arquivo provado {rel!r} nao existe mais neste repositorio. "
                f"A prova cobre uma superficie que sumiu — registre uma prova nova no genoma.")
        if faltando:
            continue
        if atual != m.get("content_hash"):
            problemas.append(
                f"{p['id']} ({p.get('title', '')[:60]}): este PR altera uma superficie provada.\n"
                f"    arquivos : {', '.join(sorted(m['paths']))}\n"
                f"    no genoma: {m.get('content_hash')}  (commit {m.get('commit')})\n"
                f"    agora    : {atual}\n"
                f"    Registre uma prova nova no genoma (liceu-genome, genome/07-proofs.yaml) "
                f"com o hash atual — ou explique no PR por que o comportamento provado nao mudou.")
        else:
            print(f"  [OK] {p['id']} superficie inalterada ({len(m['paths'])} arquivo(s))")
    return problemas


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--repo", required=True, help="nome do repositorio como o genoma o chama")
    ap.add_argument("--root", default=".", help="raiz do checkout deste repositorio")
    ap.add_argument("--proofs", default=GENOME_PROOFS_URL)
    a = ap.parse_args(argv)
    problemas = check(load_proofs(a.proofs), a.repo, Path(a.root))
    if problemas:
        print("\nSUPERFICIE PROVADA ALTERADA\n")
        for p in problemas:
            print("  x", p)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
