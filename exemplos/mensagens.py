"""
Exemplo: envio de mensagens e notificações.
"""
import unoesc

session = unoesc.abrir_sessao()

# 1. Lista alunos disponíveis para mensagem
alunos = unoesc.listar_alunos_para_mensagem(session)
print(f"Alunos disponíveis: {len(alunos)}")
if alunos:
    print(f"Colunas: {list(alunos[0].keys())}")
    print(f"Exemplo: {alunos[0]}")

# 2. Enviar mensagem para um aluno específico (descomentar para usar)
# ok = unoesc.enviar_mensagem_alunos(
#     session,
#     alunos=["450721"],           # RA do aluno (ou lista de RAs)
#     assunto="Aviso de aula",
#     mensagem="Olá! A aula de amanhã será realizada remotamente.",
# )
# print(f"Mensagem enviada: {ok}")

# 3. Enviar notificação push via Unoesc ON (descomentar para usar)
# disc = unoesc.buscar_disciplina(session, "Banco de Dados I")
# ok = unoesc.enviar_notificacao_on(
#     session,
#     mensagem="Lembrete: entrega da tarefa hoje até às 23h59.",
#     disciplinas=disc["dof"],
# )
# print(f"Notificação enviada: {ok}")
