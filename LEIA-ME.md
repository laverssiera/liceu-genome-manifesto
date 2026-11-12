# liceu-genome-manifesto

O que as CIs do ecossistema LICEU precisam do genoma (privado), e nada alem.

**Este repositorio e DERIVADO.** Nada aqui se edita a mao: o conteudo inteiro e
gerado por `tools/manifesto_publico.py` no liceu-genome, e a CI do genoma
confere byte a byte que este repositorio e o derivado do head dela.

| arquivo | o que e |
|---|---|
| `provas.json` | provas vigentes com superficie: id e `mechanism` (repo, paths, content_hash, commit) |
| `pfc.json` | falsas afirmacoes evitadas: id e os testes de regressao (repo, file, name) |
| `tools/` | as ferramentas que as CIs rodam, copias byte a byte das do genoma; entre elas a guarda de privacidade dos repositorios publicos, sem a lista de negacao, que entra por secret |

Sem titulo, nota ou evidencia de prova nenhuma. Os consumidores buscam tudo
POR SHA: `git ls-remote` no main, e daqui em diante a URL do sha.
