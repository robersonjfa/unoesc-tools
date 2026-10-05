# unoesc-tools — instruções para agentes de IA

Este arquivo é lido por agentes de código (Codex, Cursor, opencode, T3 Code, Copilot, VS Code e outros).
Ele diz o que é o projeto, o que **nunca** fazer e onde mexer. Leia antes de qualquer alteração.

## O que é

Pacote Python (`import unoesc`) que automatiza o Portal de Ensino UNOESC (`acad.unoesc.edu.br`) e o Moodle ON
(`on.unoesc.edu.br`): disciplinas, diário de classe, plano de ensino, notas, presença, mensagens, trilha do Moodle
e exportação de questionários/banco de questões. É usado por professores — não é um projeto de brinquedo:
as funções de escrita mexem na vida acadêmica de alunos reais.

## Regras invioláveis

1. **Credencial nunca entra em código, prompt, log, commit ou mensagem.** Ela vem de `UNOESC_USUARIO` /
   `UNOESC_SENHA` no ambiente, ou de um arquivo com permissão `600` que o processo lê e exporta. Se você não tem a
   credencial, **peça ao humano** — não procure, não adivinhe, não tente várias senhas.
2. **`dry_run=True` é o padrão e permanece assim.** Toda função que escreve (sync de trilha, criar seção, criar
   atividade, lançar notas) tem `dry_run` e ele só é desligado com autorização explícita do humano, na conversa.
   Mostre a prévia do que vai acontecer antes de executar.
3. **Nada apaga.** Não existe remoção implementada e não é para inventar uma.
4. **Mensagem para aluno e lançamento de nota só com ordem explícita.** `enviar_mensagem_alunos`,
   `enviar_mensagem_turmas`, `comunicar_estudantes`, `enviar_notificacao_on`, `lancar_notas_diario`,
   `importar_notas_diario` e `lancar_faltas` afetam pessoas reais. Confirme com o humano o alvo (turma, aluno,
   valor) antes de rodar — e prefira sempre a versão de leitura primeiro, para conferir.
5. **Nunca invente dado acadêmico.** Se a fonte não respondeu, diga que não respondeu. Não complete nota, turma,
   nome de aluno ou conteúdo de plano de cabeça.
6. **Dado pessoal de aluno é sensível.** Não despeje lista de alunos, telefone, e-mail ou relatório em log,
   arquivo temporário ou lugar fora do repositório do trabalho.

## Ambiente

```bash
pip install -e .          # ou: pip install -r requirements.txt
export UNOESC_USUARIO="12345"
export UNOESC_SENHA="..."  # nunca escreva isso em arquivo versionado
```

Python 3.9+. A sessão (cookies) fica em `~/.unoesc_session.json` com permissão `600`; expirada, `abrir_sessao()`
autentica de novo sozinha.

## Por onde começar

- `unoesc/__init__.py` — reexporta as 74 funções públicas. É o mapa do que existe.
- `unoesc/portal.py` — Portal UNOESC (disciplinas, diário, plano de ensino, notas, mensagens, relatórios).
- `unoesc/moodle.py` — Moodle ON (curso, seções, atividades, escrita com `dry_run`).
- `unoesc/grades.py` — exportação de notas (CSV, Excel, por atividade, formato do diário).
- `unoesc/quiz_export.py` — questionários e banco de questões para DOCX/PDF.
- `exemplos/` — um script por fluxo, todos rodáveis. **Comece por aqui** para ver o uso real de cada função.
- `README.md` — referência completa da API.

## Convenções do código

- Funções em português, no imperativo (`listar_`, `obter_`, `criar_`, `exportar_`, `lancar_`), docstring em português.
- Função fina: monta a requisição, valida, devolve `dict`/`list` — sem regra de negócio escondida.
- A primeira coisa que quase toda função recebe é a `session` autenticada.
- Toda função de escrita aceita `dry_run` e devolve o que *seria* feito quando ele está ligado.
- Ao adicionar função pública, exporte-a em `unoesc/__init__.py` (`from .modulo import ...` **e** `__all__`) —
  e cite na tabela do README. Já houve função documentada que não existia; não repita isso.

## Como testar sem estragar nada

1. Rode primeiro o exemplo correspondente em `exemplos/` — ele é somente leitura, na maioria dos casos.
2. Use as funções de leitura (`listar_*`, `obter_*`, `analisar_*`) para descobrir os termos reais de busca:
   `disciplina_termo`, `secao_termo`, `atividade_termo`.
3. Em escrita: `dry_run=True`, mostre a prévia, só depois execute.
4. Não crie turma, aluno, mensagem ou nota de teste em ambiente real.

## Erros comuns

| Sintoma | Causa provável |
|---|---|
| `Login falhou` | credencial ausente/expirada, ou variável de ambiente não exportada no processo |
| Busca não encontra a disciplina | o termo tem que casar com o formato do portal (`10276/EAD54-13`) — liste antes de buscar |
| Sessão do Moodle cai | o SSO expira: chame `abrir_curso()` de novo |
| Exportação vazia | quiz sem tentativa ou banco de questões vazio — confira com `analisar_quiz` antes |
