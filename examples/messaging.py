"""
Exemplo: comunicação com estudantes (message do portal + push Unoesc ON).

Descomente os blocos de envio apenas quando quiser disparar de fato.
"""
import unoesc

session = unoesc.open_session()

# 1. Turmas disponíveis para message
print("── Turmas ──")
turmas = unoesc.list_message_classes(session)
for t in turmas:
    print(f"  [{t['dof']}] {t['turma']} — {t['componente']} ({t['estudantes']} alunos)")

# 2. Alunos de uma discipline (por código/nome ou DOF)
DISC = "Banco de Dados"  # ajuste
print(f"\n── Alunos de '{DISC}' ──")
alunos = unoesc.list_students_for_message(session, DISC)
print(f"{len(alunos)} alunos")
for a in alunos[:5]:
    print(f"  {a['ra']}  {a['nome']}  <{a['email']}>")

# 3. Buscar por nome/RA
encontrados = unoesc.find_message_students(session, DISC, "silva")
print(f"\nBusca 'silva': {len(encontrados)} resultado(s)")

# 4. Mensagem do portal para alunos específicos (descomentar para enviar)
# ras = [alunos[0]["ra"]]
# r = unoesc.send_message_to_students(
#     session,
#     alunos=ras,
#     assunto="Aviso de aula",
#     message="Olá! A aula de amanhã será realizada remotamente.",
#     disciplines=DISC,
# )
# print("Portal:", r)

# 5. Mensagem para a turma inteira (descomentar para enviar)
# r = unoesc.send_message_to_classes(
#     session,
#     disciplines=DISC,
#     assunto="Aviso geral",
#     message="Lembrete: entrega da atividade até domingo.",
# )
# print("Turma:", r)

# 6. Push Unoesc ON (descomentar para enviar)
# r = unoesc.send_on_notification(
#     session,
#     message="Lembrete: entrega da tarefa hoje até 23h59.",
#     disciplines=DISC,
#     title="Entrega de tarefa",
# )
# print("Push:", r)

# 7. Ambos os canais de uma vez
# r = unoesc.notify_students(
#     session,
#     disciplines=DISC,
#     assunto="Aviso",
#     message="Material novo disponível na Semana 7.",
#     canais=("portal", "push"),
# )
# print(r)
