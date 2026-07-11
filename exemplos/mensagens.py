"""
Exemplo: comunicação com estudantes (mensagem do portal + push Unoesc ON).

Descomente os blocos de envio apenas quando quiser disparar de fato.
"""
import unoesc

session = unoesc.abrir_sessao()

# 1. Turmas disponíveis para mensagem
print("── Turmas ──")
turmas = unoesc.listar_turmas_mensagem(session)
for t in turmas:
    print(f"  [{t['dof']}] {t['turma']} — {t['componente']} ({t['estudantes']} alunos)")

# 2. Alunos de uma disciplina (por código/nome ou DOF)
DISC = "Banco de Dados"  # ajuste
print(f"\n── Alunos de '{DISC}' ──")
alunos = unoesc.listar_alunos_para_mensagem(session, DISC)
print(f"{len(alunos)} alunos")
for a in alunos[:5]:
    print(f"  {a['ra']}  {a['nome']}  <{a['email']}>")

# 3. Buscar por nome/RA
encontrados = unoesc.buscar_alunos_mensagem(session, DISC, "silva")
print(f"\nBusca 'silva': {len(encontrados)} resultado(s)")

# 4. Mensagem do portal para alunos específicos (descomentar para enviar)
# ras = [alunos[0]["ra"]]
# r = unoesc.enviar_mensagem_alunos(
#     session,
#     alunos=ras,
#     assunto="Aviso de aula",
#     mensagem="Olá! A aula de amanhã será realizada remotamente.",
#     disciplinas=DISC,
# )
# print("Portal:", r)

# 5. Mensagem para a turma inteira (descomentar para enviar)
# r = unoesc.enviar_mensagem_turmas(
#     session,
#     disciplinas=DISC,
#     assunto="Aviso geral",
#     mensagem="Lembrete: entrega da atividade até domingo.",
# )
# print("Turma:", r)

# 6. Push Unoesc ON (descomentar para enviar)
# r = unoesc.enviar_notificacao_on(
#     session,
#     mensagem="Lembrete: entrega da tarefa hoje até 23h59.",
#     disciplinas=DISC,
#     titulo="Entrega de tarefa",
# )
# print("Push:", r)

# 7. Ambos os canais de uma vez
# r = unoesc.comunicar_estudantes(
#     session,
#     disciplinas=DISC,
#     assunto="Aviso",
#     mensagem="Material novo disponível na Semana 7.",
#     canais=("portal", "push"),
# )
# print(r)
