# Instruções para o GitHub Copilot

As regras deste projeto estão em **`AGENTS.md`**, na raiz do repositório. Leia antes de sugerir alterações.

O que não pode ser quebrado:

- Credencial do Portal UNOESC nunca em código, prompt, log ou commit — só por `UNOESC_USUARIO` / `UNOESC_SENHA`
  no ambiente, ou arquivo com permissão `600`.
- Toda função que escreve (sync de trilha, criar seção/atividade, lançar notas) tem `dry_run` e ele fica `True`
  por padrão. Não desligue sem autorização explícita do humano.
- Nada apaga: não existe remoção implementada e não é para inventar uma.
- Mensagem para aluno, notificação e lançamento de nota só com ordem explícita — e conferindo antes com as
  funções de leitura.
- Nunca invente dado acadêmico (nota, turma, aluno, plano) e não coloque dado pessoal de aluno em log.

Mapa do projeto: `unoesc/__init__.py` (76 funções públicas reexportadas), `unoesc/portal.py` (Portal),
`unoesc/moodle.py` (Moodle ON), `unoesc/grades.py` (notas), `unoesc/quiz_export.py` (questionários),
`examples/` (um script por fluxo) e `README.md` (referência da API).

Ao criar uma função pública, exporte-a em `unoesc/__init__.py` (`from ... import ...` e `__all__`) e cite na
tabela do README — já houve função documentada que não existia.
