"""
Exemplo: navegação básica pelo portal e Moodle.
"""
import unoesc

# 1. Abre sessão (dialog de código/CPF no primeiro uso; dialog de senha a cada expiração)
session = unoesc.open_session()

# 2. Lista todas as disciplines do período atual
print("── Disciplinas ──")
for d in unoesc.list_disciplines(session):
    print(f"  [{d['dof']}] {d['codigo']} - {d['nome']}")

# 3. Busca uma discipline específica e abre no Moodle
disc = unoesc.find_discipline(session, "Banco de Dados I")
print(f"\nDisciplina: {disc}")

session, course_id = unoesc.open_course(session, disc["dof"])
print(f"Course ID no Moodle: {course_id}")

# 4. Lista seções do curso
print("\n── Seções ──")
for s in unoesc.list_sections(session, course_id):
    print(f"  [{s['section_id']}] {s['nome']}")

# 5. Busca uma seção por data e lista suas atividades
secao = unoesc.find_section(session, course_id, "27/04")
if secao:
    print(f"\n── Atividades em '{secao['nome']}' ──")
    for a in unoesc.list_activities(session, secao["section_id"]):
        print(f"  ({a['tipo']}) [{a['activity_id']}] {a['nome']}")
