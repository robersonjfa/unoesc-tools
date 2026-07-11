# unoesc-tools

Ferramentas Python para automação do [Portal de Ensino UNOESC](https://acad.unoesc.edu.br) e do [Moodle ON](https://on.unoesc.edu.br).

Permite acesso programático a disciplinas, diário de classe, plano de ensino, notas, mensagens, atividades do Moodle e exportação de questionários/banco de questões.

O pacote Python continua importável como `unoesc`.

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

### Modo interativo — macOS

No **primeiro uso**, dois dialogs nativos são exibidos:
1. **Código ou CPF** — salvo em `~/.unoesc_config.json`
2. **Senha** — solicitada a cada sessão expirada (nunca salva em disco)

```python
import unoesc
session = unoesc.abrir_sessao()
```

### Modo headless — CI / Linux / Windows / agentes

```bash
export UNOESC_USUARIO="12345"
export UNOESC_SENHA="sua_senha"
```

```python
import unoesc
session = unoesc.abrir_sessao()
```

As variáveis de ambiente têm prioridade. A sessão fica em `~/.unoesc_session.json` (perm. 600).

> **Com LLMs:** defina as env vars no shell/config do projeto — nunca peça ao agente para escrever a senha no código.

---

## Referência da API

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
| `adicionar_encontro` / `remover_encontro` / `definir_encontro_presencial` | Manutenção do quadro |
| `listar_planos_ensino` / `obter_plano_ensino` | Plano de ensino (leitura) |
| `listar_cronograma_plano` / `listar_unidades_plano` | Cronograma e unidades |
| `listar_bibliografias_plano` / `listar_avaliacoes_plano` | Bibliografia e avaliações do plano |
| `analisar_plano_trilha` | Diff read-only plano × Moodle |
| `obter_estrutura_curso` / `classificar_secao` | Estrutura da trilha no Moodle |
| `consultar_notas` | Notas consolidadas |
| `lista_presenca` / `lista_estudantes_a2` | Listas A1 / recuperação |
| `listar_alunos_para_mensagem` / `enviar_mensagem_alunos` | Mensagem acadêmica |
| `enviar_notificacao_on` | Push no app Unoesc ON |
| `listar_ocorrencias` | Observações de alunos |
| `relatorio_perfil` / `relatorio_telefones` / `relatorio_assinaturas` | Relatórios |
| `quadro_horarios` | Horários do professor |
| `listar_avaliacoes_diario` / `importar_notas_diario` | Importação CSV no diário |
| `extrair_mapa_alunos_diario` / `lancar_notas_diario` | Lançamento nota a nota |

### Moodle ON (`moodle.py`)

| Função | Descrição |
|---|---|
| `abrir_curso` | SSO JWT → `(session, course_id)` |
| `listar_secoes` / `buscar_secao` | Seções do curso |
| `listar_atividades` / `buscar_atividade` | Atividades (`quiz`, `assign`, `lti`, …) |
| `ver_tarefa` / `ver_quiz` / `ver_forum` | Detalhes |
| `baixar_recurso` | Download de arquivo |

### Notas Moodle (`grades.py`)

| Função | Descrição |
|---|---|
| `listar_itens_avaliacao` | Itens do gradebook |
| `exportar_notas_csv` / `exportar_notas_excel` | Exportação do curso |
| `exportar_notas_tarefa` / `exportar_notas_quiz` | Por atividade |
| `exportar_notas_para_portal` | CSV no formato do diário UNOESC |

### Questionários e banco (`quiz_export.py`)

| Função | Descrição |
|---|---|
| `exportar_questionario_disciplina` | Quiz → DOCX/PDF (`fonte="quiz"` ou `"banco"`) |
| `exportar_banco_questoes_disciplina` | Banco inteiro do curso → DOCX/PDF |
| `extrair_questoes_quiz` | Questões sorteadas na prévia |
| `listar_categorias_banco` / `listar_questoes_categoria` | Navegação do banco |

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
│   ├── __init__.py
│   ├── auth.py
│   ├── portal.py
│   ├── moodle.py
│   ├── grades.py
│   └── quiz_export.py
├── exemplos/
│   ├── basico.py
│   ├── notas.py
│   ├── mensagens.py
│   ├── importar_notas.py
│   └── exportar_questionario.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Arquivos gerados localmente

| Arquivo | Conteúdo |
|---|---|
| `~/.unoesc_config.json` | Código/CPF (modo interativo) |
| `~/.unoesc_session.json` | Cookies de sessão |
| `~/Downloads/*.docx` / `*.pdf` / `*.csv` / `*.xlsx` | Exportações |
