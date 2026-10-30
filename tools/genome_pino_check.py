#!/usr/bin/env python3
"""A forma do pino: citacao historica e pino vivo nao se distinguem pelo TEXTO.

O furo que este modulo fecha, medido em 2026-10-19
---------------------------------------------------
No relatorio do ecossistema eu escrevi "8 pinos, todos v0.30.0". Era verdade,
e era verdade porque o instrumento era um grep restrito a `requirements*.txt` e
`pyproject.toml`. Alargando a varredura para toda linha que cita o kit, o
ecossistema tem 43 ocorrencias de versao em 12 versoes distintas: 8 em arquivo
de instalacao, e 35 fora dele, espalhadas por onze versoes antigas.

As 35 NAO sao defeito, e a 8 nao sao virtude: sao NATUREZAS diferentes que o
texto nao separa. `v0.24.0` dentro de uma prova e o registro do que se media em
outubro, e corrigi-lo seria reescrever historia -- o schema do genoma diz, com
essas palavras, que prova apagada e historia reescrita. `@v0.15.0` no comando de
instalacao do README do kit e uma ORDEM no presente, dada hoje a quem le, e
estava quinze tags atras.

Entao um detector que julgue pelo texto erra de um dos dois lados, sempre:
estreito, deixa passar a ordem errada do README; largo, acusa 33 registros
historicos e pressiona alguem a "consertar" o passado. O falso verde e pior,
mas o falso vermelho que convida a apagar prova e pior ainda.

A distincao que FUNCIONA, e ela e de MODO e nao de forma
--------------------------------------------------------
    VIVO       o artefato afirma o estado DE AGORA: um arquivo que uma
               ferramenta LE para instalar, a propria fonte unica, ou o
               comando que o README manda executar. Tem de concordar com a
               fonte, ou e divergencia.

    HISTORIA   o artefato carrega a PROPRIA DATA: uma prova do genoma com
               campo `date`, um documento de evidencia cujo nome comeca por
               YYYY-MM-DD. Registra o que era verdade naquele dia. NAO se
               julga, nao se corrige, nao se toca.

    NAO_MENSURAVEL  nao e nem um nem outro, e a ferramenta NAO decide por
               conta propria: nomeia o arquivo e a linha, e quem le decide.
               Terceiro estado do `varredura.py` -- M < N nao e "nada
               encontrado", e nao-medicao.

O terceiro estado e o que mantem isto honesto. Um comentario de workflow que
diz "o kit vem do requirements.txt (liceu-protocol v0.NN.0)" nao traz data na
propria linha e nao e arquivo de instalacao: a ferramenta nao sabe se e nota
historica ou afirmacao velha, e dizer que sabe seria inventar. Nomeado, a
resposta fica obvia para quem le -- e, pela regra de classe, numero derivavel
de outro artefato nao se escreve, se deriva.

A fonte unica, e ela se declara
-------------------------------
`liceu_protocol/VERSION` traz as versoes dos componentes e diz de si mesma:
"Fonte unica; consumidores instalam o pacote, nao copiam." Toda citacao VIVA e
conferida contra ela. Nenhum numero deste modulo e literal.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

VIVO = "VIVO"
# DENTRO de VIVO ha duas naturezas, e conta-las juntas convida a somar
# coisas diferentes. As duas sao conferidas contra a fonte -- a distincao e
# de CONTAGEM e de leitura, nao de tratamento.
PINO = "PINO"            #: arquivo que uma FERRAMENTA le para instalar
INSTRUCAO = "INSTRUCAO"  #: comando que um HUMANO le e executa
FONTE = "FONTE"          #: a propria fonte unica
HISTORIA = "HISTORIA"
NAO_MENSURAVEL = "NAO_MENSURAVEL"

# o kit e citado por um destes dois nomes
CITA_O_KIT = re.compile(r"liceu[-_]protocol")
VERSAO = re.compile(r"v?(\d{1,2}\.\d{1,2}\.\d{1,2})")

# ARQUIVO QUE UMA FERRAMENTA LE PARA INSTALAR -> o que esta aqui e pino vivo
INSTALACAO = re.compile(
    r"(^|/)(requirements[^/]*\.txt|constraints[^/]*\.txt|pyproject\.toml|"
    r"poetry\.lock|Pipfile(\.lock)?|setup\.cfg)$")
# A FONTE UNICA, e o README que manda instalar -> tambem afirmam o agora
FONTE_UNICA = re.compile(r"(^|/)liceu_protocol/VERSION$")
README_DO_KIT = re.compile(r"(^|/)README\.md$")
# No README do kit, `componente=X.Y.Z` afirma a versao daquele componente
# AGORA, e a linha nao precisa nomear o kit para faze-lo. O filtro por linha
# passava por cima do bloco de versoes -- a maior coisa velha do repositorio.
ATRIBUI_COMPONENTE = re.compile(
    r"\b(constitution|conformance_kit|federation_sdk|registry_checker|"
    r"boundary_checker)=(\d{1,2}\.\d{1,2}\.\d{1,2})\b"
    # package_date vive no MESMO bloco e deriva da MESMA fonte. A forma e
    # data e nao versao, e por isso vai em alternativa propria -- deixa-la
    # de fora seria buraco aberto de proposito, num detector cujo trabalho
    # e justamente conferir este bloco.
    r"|\b(package_date)=(\d{4}-\d{2}-\d{2})\b")

# DOCUMENTO QUE CARREGA A PROPRIA DATA -> historia
NOME_DATADO = re.compile(r"(^|/)(\d{4}-\d{2}-\d{2})[-.]")

IGNORA = {".git", "node_modules", ".venv", "venv", "__pycache__", "build",
          "dist", ".pytest_cache", ".mypy_cache", "site-packages",
          "egg-info", "liceu_protocol.egg-info"}
EXT = {".txt", ".toml", ".yaml", ".yml", ".md", ".json", ".py", ".sh", ".cfg",
       ".lock", ""}


def le_fonte(caminho: pathlib.Path) -> dict[str, str]:
    """As versoes dos componentes, lidas da fonte que se declara fonte."""
    fora: dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8").split("\n"):
        if "=" in linha and not linha.startswith("#"):
            k, _, v = linha.partition("=")
            fora[k.strip()] = v.strip()
    if "conformance_kit" not in fora:
        raise SystemExit(f"{caminho} nao declara conformance_kit -- "
                         f"sem fonte nao ha juizo, e nao ha juizo no escuro")
    return fora


# ANCORA DE TEMPO: o que faz de um bloco um REGISTRO e nao uma afirmacao de hoje.
# `date` e a obvia. `pr` tambem e: um numero de PR aponta para um ato imutavel
# do passado, e e a `procedencia` que a UNK-0018 exige de todo registro nao
# derivavel. A ALTERNATIVA RECUSADA era lacrar uma LISTA dos blocos isentos,
# como o portao C25-06 faz com as suas tres; foi recusada por dois motivos, e o
# segundo pesa mais: lista guarda numero de LINHA, e linha se move; e com ela o
# estado "zero indecisos" fica inalcancavel para sempre, entao o terceiro estado
# deixa de ser FILA e passa a ser encolher de ombros permanente. Fila que nunca
# esvazia nao e fila. O RISCO DESTA ESCOLHA, nomeado e nao escondido: um bloco
# que ganhe um `pr` tira suas citacoes de versao do julgamento. Fica contido por
# onde passa -- `pr` em bloco do genoma vive em `source` e `prediction`, campos
# que o schema valida e o juiz confere, nao texto livre posto de passagem.
ANCORA_DE_TEMPO = re.compile(
    r"^\s+date:\s*[\"']?\d{4}-\d{2}-\d{2}"
    r"|[{,]\s*pr:\s*\d+"
    r"|^\s+pr:\s*\d+"
    # e em PROSA: `required_evidence` e `note` datam por dentro, com a data no
    # meio da frase e nao em campo. A forma do registro varia; o que nao varia
    # e ele dizer QUANDO. Exigir forma de campo deixaria historia legitima na
    # fila de indecisos para sempre, que e o defeito que esta regra evita.
    r"|\b\d{4}-\d{2}-\d{2}\b")


def blocos_com_data(texto: str) -> list[tuple[int, int]]:
    """Faixas de linha dos blocos `- id:` que trazem ancora de tempo.

    O genoma guarda historia em blocos identificados, e registro tem QUANDO:
    `date`, ou `pr`. Uma citacao de versao DENTRO de um bloco ancorado e o
    registro daquele momento, e nao afirmacao sobre hoje.
    """
    linhas = texto.split("\n")
    inicios = [i for i, l in enumerate(linhas) if re.match(r"^- id: ", l)]
    fora = []
    for n, ini in enumerate(inicios):
        fim = inicios[n + 1] if n + 1 < len(inicios) else len(linhas)
        if any(ANCORA_DE_TEMPO.search(l) for l in linhas[ini:fim]):
            # +1 nas DUAS pontas: `ini` e `fim` sao indices 0-based e a faixa e
            # comparada com numero de linha 1-based. Sem o +1 em `fim`, a ULTIMA
            # linha de todo bloco ancorado ficava fora, e uma citacao ali caia em
            # NAO_MENSURAVEL por engano -- falha aberta, achada pelo teste.
            fora.append((ini + 1, fim + 1))
    return fora


def forma_viva(rel: str) -> str | None:
    """Qual das tres naturezas de VIVO, ou None se nao for viva.

    A nona citacao viva do ecossistema e o `pip install` do README do kit, e
    nao um pino: nenhuma ferramenta a le. Ela afirma o agora e por isso e
    conferida; mas chamar as nove de "pinos" soma coisas diferentes.
    """
    if INSTALACAO.search(rel):
        return PINO
    if FONTE_UNICA.search(rel):
        return FONTE
    if README_DO_KIT.search(rel):
        return INSTRUCAO
    return None


def classifica(rel: str, num: int, datados: list[tuple[int, int]]) -> str:
    if forma_viva(rel):
        return VIVO
    if NOME_DATADO.search(rel):
        return HISTORIA
    if any(a <= num < b for a, b in datados):
        return HISTORIA
    return NAO_MENSURAVEL


def varre(raiz: pathlib.Path, fonte: dict[str, str]) -> dict:
    kit = fonte["conformance_kit"]
    achados = []
    for f in sorted(raiz.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in EXT:
            continue
        if IGNORA & {p.name for p in f.parents} or any(
                p.name.endswith(".egg-info") for p in f.parents):
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            achados.append({"natureza": NAO_MENSURAVEL, "caminho": str(f),
                            "linha": 0, "versao": None,
                            "motivo": f"nao se deixou ler: {type(e).__name__}"})
            continue
        if not CITA_O_KIT.search(txt):
            continue
        rel = str(f.relative_to(raiz)).replace("\\", "/")
        # `genome/` em QUALQUER ponto do caminho: varrendo a pasta que contem
        # os repositorios, o relativo e `liceu-genome/genome/...`, e o
        # startswith deixava 43 registros datados em NAO_MENSURAVEL.
        datados = blocos_com_data(txt) if re.search(r"(^|/)genome/", rel) else []
        eh_readme_do_kit = README_DO_KIT.search(rel) and "liceu_protocol" in txt
        for num, linha in enumerate(txt.split("\n"), 1):
            # o bloco de componentes do README do kit: cada atribuicao afirma a
            # versao DAQUELE componente, e se confere contra ELE e nao contra o kit
            if eh_readme_do_kit:
                for m in ATRIBUI_COMPONENTE.finditer(linha):
                    achados.append({
                        "natureza": VIVO, "forma": forma_viva(rel),
                        "caminho": rel, "linha": num,
                        # 1|3 e 2|4: a alternativa de package_date traz os grupos 3 e 4
                        "versao": m.group(2) or m.group(4),
                        "componente": m.group(1) or m.group(3),
                        "texto": linha.strip()[:120],
                    })
            if not CITA_O_KIT.search(linha):
                continue
            for m in VERSAO.finditer(linha):
                achados.append({
                    "natureza": classifica(rel, num, datados),
                    "forma": forma_viva(rel),
                    "caminho": rel, "linha": num, "versao": m.group(1),
                    "componente": "conformance_kit",
                    "texto": linha.strip()[:120],
                })
    vivos = [a for a in achados if a["natureza"] == VIVO]
    # cada citacao viva contra O SEU componente na fonte. Aceitar qualquer
    # componente tornaria a conferencia decorativa: `1.18.0` num requirements.txt
    # passaria porque a Constituicao esta em 1.18.0.
    divergentes = [a for a in vivos
                   if fonte.get(a.get("componente", "conformance_kit")) != a["versao"]]
    return {"kit_na_fonte": kit, "fonte": fonte, "achados": achados,
            "vivos": vivos, "divergentes": divergentes,
            "historia": [a for a in achados if a["natureza"] == HISTORIA],
            "indecisos": [a for a in achados if a["natureza"] == NAO_MENSURAVEL]}


def fonte_de(r: dict, componente: str) -> str:
    return r["fonte"].get(componente, "(componente ausente da fonte)")


def imprime(r: dict) -> int:
    print("A FORMA DO PINO — pino vivo, citacao historica, e o que nao se decide")
    print(f"  fonte unica declara conformance_kit={r['kit_na_fonte']}")
    print(f"  componentes na fonte: "
          f"{', '.join(f'{k}={v}' for k, v in r['fonte'].items() if k != 'source')}")
    print()
    por_forma = {}
    for a in r["vivos"]:
        por_forma.setdefault(a.get("forma") or "(sem forma)", []).append(a)
    print(f"  {VIVO:16} {len(r['vivos']):4}   afirmam o agora; conferidos contra a fonte")
    for f in (PINO, INSTRUCAO, FONTE):
        if f in por_forma:
            explica = {PINO: "arquivo que uma FERRAMENTA le para instalar",
                       INSTRUCAO: "comando que um HUMANO le e executa",
                       FONTE: "a propria fonte unica"}[f]
            print(f"    {f:14} {len(por_forma[f]):4}   {explica}")
    if PINO in por_forma and INSTRUCAO in por_forma:
        print("    Os dois numeros NAO se somam num so rotulo: 'pinos' sao os")
        print(f"    {len(por_forma[PINO])}, e a instrucao e outra coisa. As duas sao conferidas")
        print("    contra a fonte, e e so a CONTAGEM que se separa.")
    print(f"  {HISTORIA:16} {len(r['historia']):4}   trazem a propria data; NAO julgados")
    print(f"  {NAO_MENSURAVEL:16} {len(r['indecisos']):4}   a ferramenta nao decide; nomeados abaixo")
    print()

    if r["divergentes"]:
        print(f"  DIVERGENCIA EM PINO VIVO — {len(r['divergentes'])} ocorrencia(s).")
        print("  Estes afirmam o estado de agora e discordam da fonte unica:")
        for a in r["divergentes"]:
            c = a.get("componente", "conformance_kit")
            print(f"    {a['caminho']}:{a['linha']}  diz {c}={a['versao']}, "
                  f"a fonte diz {fonte_de(r, c)}")
            print(f"      {a['texto']}")
        print()
    else:
        print("  Nenhuma divergencia em pino vivo.")
        print()

    if r["indecisos"]:
        print(f"  NAO_MENSURAVEL — {len(r['indecisos'])} ocorrencia(s) que a")
        print("  ferramenta NAO classifica, e por isso nomeia em vez de aprovar:")
        for a in r["indecisos"]:
            print(f"    {a['caminho']}:{a['linha']}  cita {a['versao']}")
            print(f"      {a.get('texto') or a.get('motivo')}")
        print()

    if r["divergentes"]:
        print("RESULTADO: PINO VIVO DIVERGENTE DA FONTE")
        return 1
    if r["indecisos"]:
        print("RESULTADO: CITACAO DE VERSAO SEM ANCORA DE TEMPO E SEM FONTE")
        print("  Nao e 'nada encontrado': e nao-medicao, e sai com erro. Cada")
        print("  ocorrencia acima ou e afirmacao velha -- e entao o numero,")
        print("  sendo derivavel de outro artefato, se APAGA e nao se corrige --")
        print("  ou e registro, e entao lhe falta a ancora que o torna um.")
        return 1
    print("RESULTADO: TODO PINO VIVO CONCORDA COM A FONTE")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--raiz", required=True,
                   help="a arvore a varrer (um repositorio, ou a pasta que os contem)")
    p.add_argument("--fonte", required=True,
                   help="caminho do liceu_protocol/VERSION, a fonte unica")
    p.add_argument("--json", help="escreve o resultado completo neste arquivo")
    a = p.parse_args(argv)
    fonte = le_fonte(pathlib.Path(a.fonte))
    r = varre(pathlib.Path(a.raiz), fonte)
    codigo = imprime(r)
    if a.json:
        pathlib.Path(a.json).write_text(
            json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
