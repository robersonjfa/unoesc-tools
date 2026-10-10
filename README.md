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
session = unoesc.open_session()
```

As variáveis de ambiente têm prioridade sobre qualquer outra fonte.

### Modo interativo — macOS

No **primeiro uso**, dois diálogos nativos aparecem:

1. **Código ou CPF** — salvo em `~/.unoesc_config.json`
2. **Senha** — pedida a cada sessão expirada (nunca salva em disco)

```python
import unoesc
session = unoesc.open_session()
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

Os arquivos em `examples/` rodam direto e servem de receita para cada fluxo:

| Arquivo | O que mostra |
|---|---|
| `basic.py` | Navegação básica pelo portal e pelo Moodle |
| `grades_export.py` | Exportação de notas nas várias formas (CSV, Excel, por tarefa, por quiz, formato do diário) |
| `import_grades.py` | Notas do Moodle → diário do Portal UNOESC |
| `attendance.py` | Encontros do diário: consultar e lançar faltas |
| `messaging.py` | Comunicação com estudantes: mensagem do portal, mensagem por turma e push no app Unoesc ON |
| `teaching_plan_trail.py` | Ler o plano de ensino e comparar com a trilha já existente no Moodle |
| `teaching_plan_trail_sync.py` | Prévia da sincronização plano → trilha Moodle (somente `dry_run`) |
| `update_activity.py` | Atualizar datas de uma atividade existente via `modedit` (somente `dry_run`) |
| `export_quiz.py` | Questionário/banco de questões do Moodle → DOCX e PDF |

```bash
python examples/teaching_plan_trail.py
```

---

## Referência da API

76 funções públicas, todas reexportadas na raiz do pacote (`import unoesc`).

### Autenticação

| Função | Descrição |
|---|---|
| `open_session()` | Retorna `requests.Session` autenticada |

### Portal UNOESC (`portal.py`)

| Função | Descrição |
|---|---|
| `list_disciplines` / `find_discipline` | Disciplinas com `codigo`, `nome`, `dof` |
| `list_class_diaries` / `open_class_diary` | Diário de classe |
| `list_meetings` / `get_meeting_attendance` | Encontros e lista de faltas |
| `post_absences` / `save_meeting_attendance` | Lançar faltas / conteúdo do encontro |
| `add_meeting` / `remove_meeting` / `set_meeting_in_person` | Manutenção do quadro de encontros |
| `list_teaching_plans` / `get_teaching_plan` | Plano de ensino (leitura) |
| `list_plan_schedule` / `list_plan_units` | Cronograma e unidades do plano |
| `list_plan_bibliographies` / `list_plan_assessments` | Bibliografia e avaliações do plano |
| `analyze_plan_trail` | Diff somente-leitura: plano de ensino × trilha do Moodle |
| `plan_sections_from_plan` / `plan_activities_from_plan` | Calcula as seções/atividades que a trilha deveria ter |
| `plan_trail_sync` / `sync_trail_from_plan` | Prévia e execução do sync (`dry_run=True` por padrão) |
| `list_grades_summary` | Notas consolidadas |
| `list_attendance_report` / `list_a2_students` | Listas de A1 e de recuperação (A2) |
| `list_message_classes` / `list_students_for_message` / `find_message_students` | Turmas e alunos disponíveis para mensagem |
| `send_message_to_students` / `send_message_to_classes` | Envio de mensagem acadêmica |
| `notify_students` | Envio combinado (portal + notificação) |
| `send_on_notification` | Push no app Unoesc ON |
| `list_occurrences` | Observações registradas sobre alunos |
| `report_profiles` / `report_phones` / `report_signatures` | Relatórios de turma |
| `list_timetable` | Horários do professor |
| `list_diary_assessments` / `import_diary_grades` | Importação de CSV de notas no diário |
| `extract_diary_student_map` / `post_diary_grades` | Lançamento de nota aluno a aluno |

### Moodle ON (`moodle.py`)

| Função | Descrição |
|---|---|
| `open_course` | SSO via JWT → `(session, course_id)` |
| `list_sections` / `find_section` | Seções do curso |
| `list_activities` / `find_activity` | Atividades (`quiz`, `assign`, `lti`, …) |
| `classify_section` | Classifica a seção pelo conteúdo |
| `get_course_structure` | Estrutura completa da trilha |
| `create_section` / `update_section` | Escrita no Moodle (`dry_run=True` por padrão; nunca apaga) |
| `create_activity` / `update_activity` | Criar/atualizar atividade via `modedit`; datas com atalho `duedate`/`timeopen`/… (`dry_run=True`) |
| `moodle_datetime_fields` | Helper `duedate[day|month|…]` no formato Moodle |
| `get_assignment` / `get_quiz` / `get_forum` | Detalhes de cada tipo de atividade |
| `download_resource` | Download de arquivo do curso |

### Notas Moodle (`grades.py`)

| Função | Descrição |
|---|---|
| `list_grade_items` | Itens do livro de notas |
| `export_grades_csv` / `export_grades_excel` | Exportação do curso inteiro |
| `export_assignment_grades` / `export_quiz_grades` | Exportação por atividade |
| `export_grades_for_portal` | CSV no formato aceito pelo diário UNOESC |

### Questionários e banco de questões (`quiz_export.py`)

| Função | Descrição |
|---|---|
| `list_question_bank_categories` / `list_category_questions` | Navegação do banco de questões |
| `get_question` | Conteúdo de uma questão específica |
| `analyze_quiz` | Estrutura do quiz (questões, notas, tentativas) |
| `extract_quiz` / `extract_question_bank` | Extração do conteúdo para memória |
| `export_quiz_docx` / `export_quiz_pdf` | Exportação direta em cada formato |
| `export_quiz` / `export_discipline_quiz` | Quiz → DOCX/PDF (`source="quiz"` ou `"banco"`) |
| `export_question_bank` / `export_discipline_question_bank` | Banco inteiro do curso → DOCX/PDF |

```python
import unoesc

session = unoesc.open_session()

# Exportar questões de um questionário
unoesc.export_discipline_quiz(
    session,
    discipline_query="10276/EAD54-13",
    section_query="Semana 7",
    activity_query="Prova Objetiva",
    formats=("docx",),
    source="quiz",
)

# Exportar banco de questões de um curso
unoesc.export_discipline_question_bank(
    session,
    discipline_query="31965/EAD54-12",
    formats=("docx",),
)
```

---

## Estrutura

```
unoesc-tools/
├── unoesc/                 ← pacote Python (import unoesc)
│   ├── __init__.py         ← reexporta as 76 funções públicas
│   ├── auth.py
│   ├── portal.py
│   ├── moodle.py
│   ├── grades.py
│   └── quiz_export.py
├── examples/
│   ├── basic.py
│   ├── attendance.py
│   ├── messaging.py
│   ├── grades_export.py
│   ├── import_grades.py
│   ├── export_quiz.py
│   ├── teaching_plan_trail.py
│   ├── teaching_plan_trail_sync.py
│   └── update_activity.py
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
