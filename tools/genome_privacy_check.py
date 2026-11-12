#!/usr/bin/env python3
"""
genome_privacy_check — o genoma e PUBLICO; dado pessoal que entrar fica na internet.

A P-001 e uma casa real, de uma pessoa real. O que o LICEU registra sobre ela
sao PARAMETROS — municipio, zona, area do terreno, area construida, taxa de
ocupacao, coeficiente de aproveitamento, permeabilidade. Nunca identificacao.

Esta varredura recusa, em qualquer arquivo de texto do diretorio, os padroes
de FORMATO que estao em PADROES — CPF, CNPJ, e-mail, telefone, CEP,
matricula e inscricao, e os identificadores de processo municipal. A
contagem nao vai escrita aqui: ela e impressa a cada execucao a partir de
PADROES, porque este docstring ja listava seis quando eram onze.

    (aqui nao vai exemplo literal — este arquivo tambem e varrido, e exemplo
    de CPF num repositorio publico continua sendo um CPF num repositorio
    publico)

E recusa os NOMES DA LISTA DE NEGACAO, que nao estao neste repositorio: o
arquivo privacidade_negacao.json guarda so o HMAC-SHA256 de cada um, e a
chave fica nos secrets (LICEU_PRIVACY_HMAC_KEY), nunca no arquivo. Hash
simples nao serve: nome proprio brasileiro cai por dicionario em segundos.
Sem a chave, a lista NAO e conferida — e isso sai impresso.

ONDE ELA RODA. Mora no liceu-genome. O liceu-protocol, o liceu-design-tokens
e o liceu-shell a BUSCAM por SHA no liceu-genome-manifesto, que a publica
byte a byte (a CI do genoma confere a copia), sem token: o genoma e privado
desde 2026-10-25, e buscar nele deixava os publicos sem guarda. O manifesto
em si e varrido pela CI do genoma antes e depois de publicado. (Esta linha
ja disse "liceu-genome e liceu-protocol, os dois publicos", ate 2026-10-25,
e "buscam do genoma", ate 2026-11-12.)

O QUE ELA NAO FAZ sai impresso em TODA execucao, porque um verde que nao diz
o que nao olhou diz mais do que mediu:
    nao confere NOME em geral — so os da lista de negacao, e so com a chave
    le a ARVORE de trabalho, nao o HISTORICO: commit orfao nao e lido

Falso positivo se resolve com o allowlist explicito (--allow), nunca
afrouxando o padrao.

Uso:
    genome_privacy_check.py [--root DIR] [--allow REGEX ...]
    genome_privacy_check.py --gerar-negacao < nomes.txt > privacidade_negacao.json
        (pelo titular, na maquina dele, com a chave no ambiente; os nomes
        entram pela entrada padrao e este programa nunca os grava nem imprime)
Saida 0: nada encontrado, E a varredura mediu — a frase traz o numero de
arquivos conferidos. 1: encontrou (imprime arquivo, linha e o TIPO — nunca o
valor inteiro). 2: NAO MENSURAVEL — algum arquivo nao se deixou ler, e o que
nao foi lido nao foi aprovado.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import varredura

#: IDENTIFICADOR DE PROCESSO MUNICIPAL, acrescentado em 2026-10-15.
#:
#: A guarda procurava CPF, CNPJ, telefone e e-mail, e deixava passar contador de
#: protocolo, numero de guia e numero de recibo. Eles AMARRAM IMOVEL E
#: PROPRIETARIO pelo sistema da Prefeitura tao bem quanto um CPF: com o contador
#: do protocolo e o municipio, qualquer um consulta o processo. A FIT-014 vale
#: para eles.
#:
#: MEDIDO NO DIA EM QUE ESTA REGRA NASCEU: o genoma PUBLICO carregava CINCO
#: deles numa unica nota -- dois contadores de protocolo, dois numeros de guia e
#: um de recibo. A guarda rodava verde sobre eles havia dias, porque o que ela
#: procurava era outra coisa.
#:
#: MEDIDO ANTES DE ACRESCENTAR, e por isso sao QUATRO e nao seis: o padrao
#: `matricula/inscricao imobiliaria`, que JA existia, cobre matricula E
#: inscricao cadastral. Na primeira versao eu acrescentei os dois assim
#: mesmo, sem conferir o que havia, e eram duplicatas puras -- o teste da
#: mascara e que pegou, exigindo amostra para cada padrao.
#:
#: O VALOR NUNCA E IMPRESSO, pela mesma razao que vale para os outros: o log da
#: CI tambem e publico.
PADROES = {
    "contador de protocolo municipal": re.compile(
        r"(?i)\b(?:contador|protocolo)\D{0,12}\d{5,8}\b"),
    "numero de guia municipal": re.compile(r"(?i)\bguia\s+n?o?\s*\d{2,6}\b"),
    "numero de recibo": re.compile(r"(?i)\brecibo\s+n?o?\s*\d{3,}\b"),
    "ART/RRT": re.compile(r"(?i)\b(?:art|rrt)\D{0,6}\d{10,}\b"),
    "CPF": re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
    "CPF sem pontuacao": re.compile(r"(?i)\bcpf\D{0,10}\d{11}\b"),
    "CNPJ": re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),
    "e-mail": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "telefone BR": re.compile(r"(?:\+55[\s-]?)?\(?\b\d{2}\)?[\s-]?9?\d{4}[\s-]?\d{4}\b"),
    "matricula/inscricao imobiliaria": re.compile(r"(?i)\b(matr[ií]cula|inscri[çc][ãa]o\s+(?:imobili[áa]ria|cadastral))\D{0,10}\d"),
    "CEP": re.compile(r"\b\d{5}-\d{3}\b"),
}

#: DOMINIOS DO ECOSSISTEMA que o padrao de e-mail le como endereco, e nao sao.
#:
#: O falso positivo (PRF-0328): o ARCHIMEDES escreve tipo-de-evento + arroba +
#: produtor, e `liceu.cefeida` tem ponto e rotulo final de letras -- casa o
#: e-mail. Decidido pelo titular em 2026-10-27 (UNK-0023), com tres regras:
#:
#:   IGUALDADE EXATA do dominio inteiro, nunca prefixo nem curinga. `liceu.`
#:   sozinho cegaria a guarda para liceu.com.br, o dominio com mais chance de
#:   carregar e-mail de cliente. E x-arroba-liceu.cefeida.com continua pego.
#:   NENHUM rotulo final pode ser TLD publico: dominio registravel pode ter
#:   e-mail real. MEDIDO contra tools/iana_tlds.txt (a lista da IANA de 28/10/2026):
#:   liceu.academy, liceu.legal e liceu.market sao produtores do registry e
#:   FICARAM DE FORA, porque .academy, .legal e .market existem. O teste
#:   confere de novo contra o snapshot; a lista da IANA cresce, e o snapshot
#:   tem de ser renovado (C7). ORIGEM do snapshot: data.iana.org/TLD/
#:   tlds-alpha-by-domain.txt, baixado em 28/10/2026, sha256 do original
#:   2bb3dd32aaf48fac37f0ffa0ee586af1fbbfde2f02b79910681dc200434dcd58; guardado
#:   SEM a linha de cabecalho, porque o numero de versao dela tem forma de
#:   telefone e a propria guarda o acusava.
#:   Lista que fica velha falha ALTO: produtor novo vira falso positivo novo,
#:   barulho, e alguem acrescenta uma linha. Regra esperta fica velha em
#:   silencio. E a direcao que um repositorio publico pode pagar.
DOMINIOS_DO_ECOSSISTEMA = frozenset({
    "liceu.anchor", "liceu.archimedes", "liceu.authority", "liceu.bim", "liceu.cea",
    "liceu.cefeida", "liceu.core", "liceu.econotech", "liceu.hub", "liceu.john",
    "liceu.opera", "liceu.research", "liceu.suppliers",
})


def casa(tipo: str, rx: re.Pattern, linha: str) -> bool:
    """O padrao casa a linha? No e-mail, um casamento cujo dominio inteiro e do
    ecossistema nao conta -- os outros casamentos da mesma linha contam."""
    if tipo != "e-mail":
        return rx.search(linha) is not None
    return any(m.group(0).split("@", 1)[1].lower() not in DOMINIOS_DO_ECOSSISTEMA
               for m in rx.finditer(linha))

# Extensoes de texto que valem varrer. Binario nao entra.
EXTENSOES = {".yaml", ".yml", ".json", ".md", ".py", ".txt", ".cfg", ".toml", ".html", ".csv"}
IGNORAR = {".git", "__pycache__", "node_modules", ".venv", "build", "dist"}

# A LISTA DE NEGACAO. No genoma, o arquivo mora ao lado deste. Nos publicos a
# guarda vem do manifesto e a lista NAO vai junto (2026-11-12): ela entra pelo
# ambiente, no secret LICEU_PRIVACY_NEGACAO, ao lado da chave. O mecanismo e
# publico; o que identifica alguem, nao.
NEGACAO = Path(__file__).resolve().parent / "privacidade_negacao.json"
CHAVE_ENV = "LICEU_PRIVACY_HMAC_KEY"
NEGACAO_ENV = "LICEU_PRIVACY_NEGACAO"


def normalizar(texto: str) -> list[str]:
    """Palavras sem acento, em minusculas. 'Joao' e 'JOÃO' sao o mesmo nome."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.findall(r"[a-z0-9]+", sem_acento.lower())


def digerir(chave: bytes, palavras: list[str]) -> str:
    return hmac.new(chave, " ".join(palavras).encode("utf-8"), hashlib.sha256).hexdigest()


def carregar_negacao(caminho: Path = NEGACAO) -> dict | None:
    """{"comprimentos": {n, ...}, "digests": {hex, ...}} — ou None se nao ha lista.

    O ambiente vence o arquivo: e assim que a lista chega aos publicos sem
    ser publicada com a guarda."""
    do_ambiente = os.environ.get(NEGACAO_ENV, "")
    if do_ambiente:
        bruto = json.loads(do_ambiente)
    elif caminho.is_file():
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
    else:
        return None
    return {"comprimentos": {int(n) for n in bruto.get("comprimentos", [])},
            "digests": set(bruto.get("digests", []))}


def chave_do_ambiente() -> bytes | None:
    v = os.environ.get(CHAVE_ENV, "")
    return v.encode("utf-8") if v else None


def nomes_conferidos(negacao: dict | None, chave: bytes | None) -> int:
    # Nome so conta como conferido com a chave E com entradas. Lista sem a
    # chave tem entradas e confere zero.
    return len(negacao["digests"]) if (negacao and negacao["digests"] and chave) else 0


def limites(negacao: dict | None, chave: bytes | None) -> list[str]:
    """O que esta execucao NAO conferiu. Impresso SEMPRE, verde ou vermelho."""
    if negacao is None:
        lista = f"lista de negacao AUSENTE (nem {NEGACAO_ENV} nem privacidade_negacao.json): nenhum nome conferido"
    elif not negacao["digests"]:
        lista = "lista de negacao VAZIA: nenhum nome conferido"
    elif chave is None:
        lista = (f"lista de negacao NAO conferida: sem a chave ({CHAVE_ENV}) — "
                 f"{len(negacao['digests'])} entrada(s) ficaram de fora")
    else:
        lista = f"lista de negacao conferida: {len(negacao['digests'])} entrada(s), por HMAC"
    # O escopo em numero, na primeira linha (pedido do titular, 2026-11-12).
    nomes = nomes_conferidos(negacao, chave)
    return [f"ESCOPO desta execucao: {len(PADROES)} padroes conferidos · {nomes} nomes conferidos",
            f"LIMITES — os {len(PADROES)} padroes sao de FORMATO",
            "  NAO confere NOME em geral",
            f"  {lista}",
            "  le a ARVORE de trabalho, NAO o historico: commit orfao nao e lido"]


def alvos(root: Path) -> list[Path]:
    """Os arquivos que esta varredura se propoe a conferir — o DENOMINADOR."""
    return [f for f in sorted(root.rglob("*"))
            if f.is_file() and f.suffix.lower() in EXTENSOES
            and not any(parte in IGNORAR for parte in f.parts)]


def scan(root: Path, allow: list[re.Pattern] | None = None, negacao: dict | None = None,
         chave: bytes | None = None) -> varredura.Resultado:
    """Um arquivo, uma resposta. Arquivo que nao se deixa ler NAO conta limpo.

    Antes de 2026-10-01 isto era `except OSError: continue`: o arquivo sumia da
    conta, e o silencio dele era lido como limpeza — num guarda que protege
    repositorio PUBLICO de dado pessoal. Agora a varredura inteira vira
    NAO_MENSURAVEL, com o nome do arquivo e o motivo.

    A lista de negacao so e conferida com a chave E com entradas: cada janela
    de N palavras da linha, com N nos comprimentos da lista, vira HMAC e e
    comparada. O nome nunca e reconstruido nem impresso — so o tamanho dele.
    """
    allow = allow or []
    nomes = negacao if (negacao and negacao["digests"] and chave) else None

    def conferir(f: Path) -> list[str]:
        rel = f.relative_to(root).as_posix()
        # Sem try: a excecao E a resposta "nao consegui ler", e quem a trata e
        # a regra de varredura, nao este laco.
        linhas = f.read_text(encoding="utf-8", errors="replace").splitlines()
        achados = []
        for i, linha in enumerate(linhas, 1):
            if any(a.search(linha) for a in allow):
                continue
            for tipo, rx in PADROES.items():
                if casa(tipo, rx, linha):
                    # NUNCA imprimir o valor: o log da CI tambem e publico.
                    achados.append(f"{rel}:{i}: possivel {tipo}")
            if nomes:
                palavras = normalizar(linha)
                for n in sorted(nomes["comprimentos"]):
                    if any(digerir(chave, palavras[k:k + n]) in nomes["digests"]
                           for k in range(len(palavras) - n + 1)):
                        achados.append(f"{rel}:{i}: nome da lista de negacao ({n} palavra(s))")
        return achados

    return varredura.responder_por_item(
        alvos(root), conferir, nome=lambda f: f.relative_to(root).as_posix())


def gerar_negacao(nomes: list[str], chave: bytes) -> dict:
    """O arquivo da lista, a partir dos nomes. Roda na maquina do titular."""
    entradas = [normalizar(n) for n in nomes if n.strip()]
    return {"algoritmo": "HMAC-SHA256",
            "normalizacao": "NFKD sem acento, minusculas, palavras [a-z0-9]+ unidas por um espaco",
            "chave": f"variavel de ambiente {CHAVE_ENV}; nunca neste arquivo",
            "comprimentos": sorted({len(e) for e in entradas}),
            "digests": sorted({digerir(chave, e) for e in entradas})}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--root", default=".")
    ap.add_argument("--allow", action="append", default=[],
                    help="regex de linha isenta; use para falso positivo conhecido, com comentario")
    ap.add_argument("--gerar-negacao", action="store_true",
                    help="le nomes da entrada padrao e imprime o JSON da lista (exige a chave)")
    a = ap.parse_args(argv)
    chave = chave_do_ambiente()

    if a.gerar_negacao:
        if chave is None:
            print(f"{CHAVE_ENV} ausente: sem a chave, a lista nao pode ser gerada.", file=sys.stderr)
            return 2
        print(json.dumps(gerar_negacao(sys.stdin.read().splitlines(), chave), indent=2))
        return 0

    negacao = carregar_negacao()
    for linha in limites(negacao, chave):
        print(linha)
    print()
    r = scan(Path(a.root), [re.compile(x) for x in a.allow], negacao, chave)
    # O escopo inteiro numa linha, com o denominador, no verde e no vermelho.
    print(f"ESCOPO conferido: {len(PADROES)} padroes conferidos · "
          f"{nomes_conferidos(negacao, chave)} nomes conferidos · {r.itens} arquivos\n")
    achados = [x for lista in r.respostas for x in lista]
    if achados:
        print("DADO PESSOAL EM REPOSITORIO PUBLICO\n")
        for x in achados:
            print("  x", x)
        print("\nO tipo e dito; o valor NAO e impresso (o log da CI tambem e publico).")
        print("Remova o dado. Parametro (zona, area, indice) pode; identificacao, nao.")
        return 1
    # Achado nenhum so vira aprovacao quando a varredura MEDIU, e o numero de
    # arquivos vai SEMPRE na frase: sem ele, quem le nao distingue um
    # repositorio limpo de uma varredura que nao leu nada.
    if not r.mediu:
        print(r.resumo())
        return 0 if r.estado == varredura.NADA_A_CONFERIR else 2
    print(f"nenhum padrao de dado pessoal encontrado em {r.itens} arquivo(s) conferido(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
