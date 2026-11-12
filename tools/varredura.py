#!/usr/bin/env python3
"""N itens, N respostas — ou NAO_MENSURAVEL.

Uma varredura que itera sobre N itens e produz M < N respostas nao mediu os
N-M restantes: ela os IGNOROU. Quando o resultado e "nada encontrado", medir e
ignorar viram o MESMO texto — e o texto e tranquilizador.

O erro que motivou este modulo, em 2026-10-01: uma varredura de CI percorreu os
19 repositorios do ecossistema e reportou "nenhum vermelho". O comando que ela
chamava saia com erro — `gh run list` nao tem `--arg` — e devolvia saida vazia
nas 19 iteracoes. O laco tratou vazio como "nada encontrado" e imprimiu que a
varredura havia concluido. MEDIU ZERO REPOSITORIOS E RELATOU TRANQUILIDADE. Um
dos 19 estava vermelho.

O falso verde e pior que o falso vermelho: o falso vermelho se desfaz quando
alguem vai olhar, e o falso verde nao convida ninguem a olhar.

Tres estados, e o terceiro e o que faltava
------------------------------------------
    MEDIDO           os N itens responderam. "Nada encontrado" aqui vale.
    NADA_A_CONFERIR  N = 0. Nao e aprovacao: e ausencia de material.
    NAO_MENSURAVEL   M < N. Nao e "nada encontrado": e nao-medicao, e os itens
                     sem resposta sao NOMEADOS, com o motivo de cada um.

O ecossistema ja tinha esse terceiro estado em dois lugares e nao o aplicava
nas ferramentas de medicao: o ACTIVE_UNOBSERVABLE do plano de autoridade (nao
alcancei a Ativa nao e a Ativa esta bem) e o NAO_MENSURAVEL da prova de
revogacao. O INDETERMINADO da guarda de borda e o mesmo principio dentro de uma
linha. Aqui ele vale para a varredura inteira.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

MEDIDO = "MEDIDO"
NADA_A_CONFERIR = "NADA_A_CONFERIR"
NAO_MENSURAVEL = "NAO_MENSURAVEL"


@dataclass
class Resultado:
    estado: str
    respostas: list[Any] = field(default_factory=list)
    # (item, motivo) — o motivo e obrigatorio: "nao respondeu" sem porque nao
    # ajuda ninguem a consertar.
    sem_resposta: list[tuple[str, str]] = field(default_factory=list)
    itens: int = 0

    @property
    def mediu(self) -> bool:
        """So MEDIDO autoriza a frase de aprovacao."""
        return self.estado == MEDIDO

    def resumo(self) -> str:
        if self.estado == NADA_A_CONFERIR:
            return ("NADA FOI CONFERIDO: a varredura nao encontrou item nenhum.\n"
                    "Isto NAO e um resultado limpo: e ausencia de material para conferir.")
        if self.estado == NAO_MENSURAVEL:
            linhas = [f"NAO MENSURAVEL: {len(self.sem_resposta)} de {self.itens} "
                      f"item(ns) nao responderam.",
                      "Uma varredura incompleta NAO e 'nada encontrado' — o que nao foi "
                      "lido nao foi aprovado."]
            linhas += [f"  ? {item}  ->  {motivo}" for item, motivo in self.sem_resposta]
            return "\n".join(linhas)
        return f"{self.itens} item(ns) conferido(s)"


def motivo_de(e: BaseException) -> str:
    """O porque, SEM caminho absoluto.

    `str(FileNotFoundError)` traz o caminho inteiro, e o item ja foi nomeado em
    relativo. Num repositorio publico cujo log de CI tambem e publico, repetir
    o caminho da maquina de quem rodou e vazamento gratuito — a mesma razao
    pela qual esta varredura nunca imprime o VALOR que encontrou.
    """
    detalhe = getattr(e, "strerror", None) or str(e).splitlines()[0] if str(e) else ""
    return f"{type(e).__name__}: {detalhe}".rstrip(": ")


def responder_por_item(itens: Iterable, responder: Callable[[Any], Any], *,
                       nome: Callable[[Any], str] = str) -> Resultado:
    """Chama `responder` para CADA item e exige que todos respondam.

    `responder` devolve a resposta do item; se levantar excecao, o item fica
    SEM RESPOSTA e a varredura inteira vira NAO_MENSURAVEL. Engolir a excecao
    e seguir — `except OSError: continue` — e exatamente o defeito: o item
    desaparece da conta e o silencio dele e lido como limpeza.
    """
    itens = list(itens)
    resultado = Resultado(estado=MEDIDO, itens=len(itens))
    if not itens:
        resultado.estado = NADA_A_CONFERIR
        return resultado
    for item in itens:
        try:
            resultado.respostas.append(responder(item))
        except Exception as e:                      # noqa: BLE001 — o motivo vai no relatorio
            resultado.sem_resposta.append((nome(item), motivo_de(e)))
    if resultado.sem_resposta:
        resultado.estado = NAO_MENSURAVEL
    return resultado
