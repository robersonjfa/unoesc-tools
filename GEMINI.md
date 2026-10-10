# GEMINI.md

As instruções deste projeto estão em **`AGENTS.md`**, na raiz do repositório. Leia esse arquivo por completo antes
de mexer em qualquer coisa e siga as regras dele.

Resumo do que não pode ser quebrado:

- Credencial do portal só por variável de ambiente (`UNOESC_USUARIO` / `UNOESC_SENHA`) ou arquivo com permissão
  `600` — nunca em código, prompt, log ou commit.
- `dry_run=True` é o padrão em toda função de escrita e só é desligado com autorização explícita do humano.
- Mensagem para aluno e lançamento de nota exigem ordem explícita; confira antes com as funções de leitura.
- Nunca invente dado acadêmico, e não coloque dado pessoal de aluno em log ou arquivo temporário.

Mapa rápido: `unoesc/__init__.py` (funções públicas), `examples/` (um script por fluxo), `README.md`
(referência da API completa).
