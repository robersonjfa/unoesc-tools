# unoesc-tools

Ferramentas Python para automação do [Portal de Ensino UNOESC](https://acad.unoesc.edu.br) e do [Moodle ON](https://on.unoesc.edu.br).

Dá acesso programático a disciplinas, diário de classe, plano de ensino, notas, mensagens e atividades do Moodle, além da exportação de questionários e bancos de questões. O pacote continua importável como `unoesc`.

---

## Segurança e limites

- **Nada apaga nada.** As funções de escrita no Moodle criam e atualizam seções e atividades; não existe remoção implementada.
- **`dry_run=True` é o padrão** em tudo que escreve (sync de trilha, criação de seção/atividade). Para valer, precisa ser desligado explicitamente.
- **Credencial nunca fica no código.** Vem de variável de ambiente ou de arquivo com permissão `600` (ver *Autenticação*).
- A sessão (cookies) fica em `~/.unoesc_session.json`, permissão `600`.

---

## Instalação

```bash
cd unoesc-tools
pip install -e .
```

Ou só as dependências:

```bash
pip install -r requirements.txt
```

---

## Autenticação

### Modo headless — CI / Linux / Windows / agentes

```bash
export UNOESC_USUARIO="12345"
export UNOESC_SENHA="sua_senha"
```

```python
import unoesc
session = unoesc.abrir_sessao()
```

As variáveis de ambiente têm prioridade sobre qualquer outra fonte.

### Modo interativo — macOS

No **primeiro uso**, dois diálogos nativos aparecem:

1. **Código ou CPF** — salvo em `~/.unoesc_config.json`
2. **Senha** — pedida a cada sessão expirada (nunca salva em disco)

```python
import unoesc
session = unoesc.abrir_sessao()
```

### Usando com agentes / LLM

O caminho recomendado é o agente **ler a credencial de um arquivo com permissão `600`** e exportá-la como variável de ambiente no processo — nunca escrever a senha no código, em prompt ou em log:

```bash
# arquivo ~/.minha-credencial (chmod 600), com duas linhas: USUARIO=... / SENHA=...
export UNOESC_USUARIO="$(grep -m1 '^USUARIO=' ~/.minha-credencial | cut -d= -f2-)"
export UNOESC_SENHA="$(grep -m1 '^SENHA=' ~/.minha-credencial | cut -d= -f2-)"
```

> Nunca peça ao agente para digitar a senha no meio da conversa, e nunca aceite que ele a escreva em arquivo versionado.

---

## Plugando em agentes de IA

O repositório já vem com os arquivos de instrução que os agentes de código leem. Não precisa configurar nada:
abra o projeto na ferramenta e ela encontra as regras sozinha.

| Ferramenta | Arquivo que ela lê | Incluso |
|---|---|---|
| Codex (OpenAI), opencode, T3 Code, Jules, Warp, Roo Code, Kilo Code, goose, VS Code | `AGENTS.md` | ✅ |
| Claude Code | `CLAUDE.md` (que importa o `AGENTS.md`) | ✅ |
| Cursor | `.cursor/rules/unoesc-tools.mdc` e o `AGENTS.md` | ✅ |
| Gemini CLI | `GEMINI.md` | ✅ |
| GitHub Copilot (CLI e VS Code) | `.github/copilot-instructions.md` | ✅ |

O **`AGENTS.md`** é o arquivo principal: é nele que estão as regras invioláveis — credencial fora do código,
`dry_run=True` por padrão, nada apaga, mensagem para aluno e lançamento de nota só com ordem explícita, e nunca
inventar dado acadêmico. Os demais arquivos são cascas finas que apontam para ele, de modo que melhorar a regra
em um lugar melhora para todos.

**Como saber que plugou:** depois de instalar, peça ao agente *"liste minhas disciplinas usando o unoesc-tools"*.
Se vier a lista, está funcionando. Para conferir que ele entendeu os limites, pergunte *"posso rodar o sync da
trilha?"* — a resposta certa é que roda em `dry_run`, com prévia antes de executar.

> **MCP:** hoje o acesso é por código Python — o agente importa `unoesc` e chama as funções. Um servidor MCP
> dedicado ainda não existe; é o próximo passo natural, se for útil.

---

## Exemplos

Os arquivos em `exemplos/` rodam direto e servem de receita para cada fluxo:

| Arquivo | O que mostra |
|---|---|
| `basico.py` | Navegação básica pelo portal e pelo Moodle |
| `notas.py` | Exportação de notas nas várias formas (CSV, Excel, por tarefa, por quiz, formato do diário) |
| `importar_notas.py` | Notas do Moodle → diário do Portal UNOESC |
| `presenca.py` | Encontros do diário: consultar e lançar faltas |
| `mensagens.py` | Comunicação com estudantes: mensagem do portal, mensagem por turma e push no app Unoesc ON |
| `plano_trilha.py` | Ler o plano de ensino e comparar com a trilha já existente no Moodle |
| `plano_trilha_sync.py` | Prévia da sincronização plano → trilha Moodle (somente `dry_run`) |
| `exportar_questionario.py` | Questionário/banco de questões do Moodle → DOCX e PDF |

```bash
python exemplos/plano_trilha.py
```

---

## Referência da API

74 funções públicas, todas reexportadas na raiz do pacote (`import unoesc`).

### Autenticação

| Função | Descrição |
|---|---|
| `abrir_sessao()` | Retorna `requests.Session` autenticada |

### Portal UNOESC (`portal.py`)

| Função | Descrição |
|---|---|
| `listar_disciplinas` / `buscar_disciplina` | Disciplinas com `codigo`, `nome`, `dof` |
| `listar_diarios` / `abrir_diario` | Diário de classe |
| `listar_encontros` / `obter_presencas_encontro` | Encontros e lista de faltas |
| `lancar_faltas` / `salvar_presencas_encontro` | Lançar faltas / conteúdo do encontro |
| `adicionar_encontro` / `remover_encontro` / `definir_encontro_presencial` | Manutenção do quadro de encontros |
| `listar_planos_ensino` / `obter_plano_ensino` | Plano de ensino (leitura) |
| `listar_cronograma_plano` / `listar_unidades_plano` | Cronograma e unidades do plano |
| `listar_bibliografias_plano` / `listar_avaliacoes_plano` | Bibliografia e avaliações do plano |
| `analisar_plano_trilha` | Diff somente-leitura: plano de ensino × trilha do Moodle |
| `planejar_secoes_do_plano` | Calcula as seções que a trilha deveria ter |
| `planejar_atividades_do_plano` | Calcula as atividades de cada seção |
| `planejar_sincronizacao_trilha` / `sincronizar_trilha_do_plano` | Prévia e execução do sync (`dry_run=True` por padrão) |
| `consultar_notas` | Notas consolidadas |
| `lista_presenca` / `lista_estudantes_a2` | Listas de A1 e de recuperação (A2) |
| `listar_alunos_para_mensagem` / `buscar_alunos_mensagem` | Localizar alunos para mensagem |
| `listar_turmas_mensagem` | Turmas disponíveis para envio |
| `enviar_mensagem_alunos` / `enviar_mensagem_turmas` | Envio de mensagem acadêmica |
| `comunicar_estudantes` | Envio combinado (portal + notificação) |
| `enviar_notificacao_on` | Push no app Unoesc ON |
| `listar_ocorrencias` | Observações registradas sobre alunos |
| `relatorio_perfil` / `relatorio_telefones` / `relatorio_assinaturas` | Relatórios de turma |
| `quadro_horarios` | Horários do professor |
| `listar_avaliacoes_diario` / `importar_notas_diario` | Importação de CSV de notas no diário |
| `extrair_mapa_alunos_diario` / `lancar_notas_diario` | Lançamento de nota aluno a aluno |

### Moodle ON (`moodle.py`)

| Função | Descrição |
|---|---|
| `abrir_curso` | SSO via JWT → `(session, course_id)` |
| `listar_secoes` / `buscar_secao` | Seções do curso |
| `listar_atividades` / `buscar_atividade` | Atividades (`quiz`, `assign`, `lti`, …) |
| `classificar_secao` | Classifica a seção pelo conteúdo |
| `obter_estrutura_curso` | Estrutura completa da trilha |
| `criar_secao` / `atualizar_secao` / `criar_atividade` | Escrita no Moodle (`dry_run=True` por padrão; nunca apaga) |
| `ver_tarefa` / `ver_quiz` / `ver_forum` | Detalhes de cada tipo de atividade |
| `baixar_recurso` | Download de arquivo do curso |

### Notas Moodle (`grades.py`)

| Função | Descrição |
|---|---|
| `listar_itens_avaliacao` | Itens do livro de notas |
| `exportar_notas_csv` / `exportar_notas_excel` | Exportação do curso inteiro |
| `exportar_notas_tarefa` / `exportar_notas_quiz` | Exportação por atividade |
| `exportar_notas_para_portal` | CSV no formato aceito pelo diário UNOESC |

### Questionários e banco de questões (`quiz_export.py`)

| Função | Descrição |
|---|---|
| `listar_categorias_banco` / `listar_questoes_categoria` | Navegação do banco de questões |
| `obter_questao` | Conteúdo de uma questão específica |
| `analisar_quiz` | Estrutura do quiz (questões, notas, tentativas) |
| `extrair_questionario` / `extrair_banco_questoes` | Extração do conteúdo para memória |
| `exportar_questionario_docx` / `exportar_questionario_pdf` | Exportação direta em cada formato |
| `exportar_questionario` / `exportar_questionario_disciplina` | Quiz → DOCX/PDF (`fonte="quiz"` ou `"banco"`) |
| `exportar_banco_questoes` / `exportar_banco_questoes_disciplina` | Banco inteiro do curso → DOCX/PDF |

```python
import unoesc

session = unoesc.abrir_sessao()

# Exportar questões de um questionário
unoesc.exportar_questionario_disciplina(
    session,
    disciplina_termo="10276/EAD54-13",
    secao_termo="Semana 7",
    atividade_termo="Prova Objetiva",
    formatos=("docx",),
    fonte="quiz",
)

# Exportar banco de questões de um curso
unoesc.exportar_banco_questoes_disciplina(
    session,
    disciplina_termo="31965/EAD54-12",
    formatos=("docx",),
)
```

---

## Estrutura

```
unoesc-tools/
├── unoesc/                 ← pacote Python (import unoesc)
│   ├── __init__.py         ← reexporta as 74 funções públicas
│   ├── auth.py
│   ├── portal.py
│   ├── moodle.py
│   ├── grades.py
│   └── quiz_export.py
├── exemplos/
│   ├── basico.py
│   ├── notas.py
│   ├── importar_notas.py
│   ├── presenca.py
│   ├── mensagens.py
│   ├── plano_trilha.py
│   ├── plano_trilha_sync.py
│   └── exportar_questionario.py
├── AGENTS.md               ← instruções para agentes de IA (arquivo principal)
├── CLAUDE.md               ← Claude Code (importa o AGENTS.md)
├── GEMINI.md               ← Gemini CLI
├── .cursor/rules/          ← Cursor
├── .github/                ← GitHub Copilot
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Arquivos gerados localmente

| Arquivo | Conteúdo |
|---|---|
| `~/.unoesc_config.json` | Código/CPF (modo interativo) |
| `~/.unoesc_session.json` | Cookies de sessão (permissão `600`) |
| `~/Downloads/*.docx` / `*.pdf` / `*.csv` / `*.xlsx` | Exportações |

## Requisitos

Python 3.9+ e as dependências de `requirements.txt` (`requests`, `beautifulsoup4`, `python-docx`, `openpyxl`, `fpdf2`, entre outras).
