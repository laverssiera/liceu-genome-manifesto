#!/usr/bin/env python3
"""
privacidade_ci — a guarda de privacidade de um repositorio PUBLICO, com a
prova de que ela enxerga, na mesma execucao.

Roda tres coisas, e qualquer uma que falhe derruba o passo:

  1. A GUARDA sobre o repositorio (--root): o resultado dela e o resultado
     daqui -- 0 limpo, 1 achado, 2 nao mensuravel.
  2. O CONTROLE: uma isca de formato, montada em tempo de execucao numa pasta
     temporaria e nunca gravada no repositorio, tem de ser REPROVADA. Guarda
     que nao reprova a isca e guarda cega, e o verde dela nao diz nada.
  3. A MUTACAO: a mesma isca, com os padroes da guarda removidos, tem de
     PASSAR. E o que mostra que a reprovacao do passo 2 veio dos padroes, e
     nao de outra coisa (um arquivo ilegivel, um erro, a pasta errada).

Por que aqui e nao so nos testes do genoma: a regra do cronograma (S2) diz que
nenhum portao entra sem o seu teste de mutacao na mesma PR. Os publicos
recebem a guarda pelo manifesto; o controle e a mutacao viajam junto e rodam
em CADA execucao, contra a copia que o publico de fato baixou.

Uso: privacidade_ci.py [--root DIR]
"""
from __future__ import annotations

import argparse
import contextlib
import io
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genome_privacy_check as gpc  # noqa: E402

# Montada por concatenacao: este arquivo tambem e varrido, e a isca literal
# casaria com o proprio padrao. E um CEP de formato, sem dono.
ISCA = "cep " + "12345" + "-" + "678" + "\n"


def _calado(argv: list[str]) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return gpc.main(argv)


def controle_e_mutacao() -> tuple[int, int]:
    """(rc da guarda sobre a isca, rc da guarda SEM padroes sobre a mesma isca)."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "isca.md").write_text(ISCA, encoding="utf-8")
        com = _calado(["--root", d])
        guardados = dict(gpc.PADROES)
        gpc.PADROES.clear()
        try:
            sem = _calado(["--root", d])
        finally:
            gpc.PADROES.update(guardados)
    return com, sem


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--root", default=".")
    a = ap.parse_args(argv)

    rc = gpc.main(["--root", a.root])
    com, sem = controle_e_mutacao()
    print()
    print(f"CONTROLE: isca de formato numa pasta temporaria -> rc {com} (tem de ser 1, REPROVADA)")
    print(f"MUTACAO:  a mesma isca sem os padroes da guarda -> rc {sem} (tem de ser 0, PASSA)")
    if com != 1 or sem != 0:
        print("\nA GUARDA NAO PROVOU QUE ENXERGA: o verde acima nao vale.")
        return 3
    return rc


if __name__ == "__main__":
    sys.exit(main())
