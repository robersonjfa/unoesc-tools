"""
Exemplo: navegação básica pelo portal e Moodle.
"""
import unoesc

# 1. Abre sessão (dialog de código/CPF no primeiro uso; dialog de senha a cada expiração)
session = unoesc.abrir_sessao()

# 2. Lista todas as disciplinas do período atual
print("── Disciplinas ──")
for d in unoesc.listar_disciplinas(session):
    print(f"  [{d['dof']}] {d['codigo']} - {d['nome']}")

# 3. Busca uma disciplina específica e abre no Moodle
disc = unoesc.buscar_disciplina(session, "Banco de Dados I")
print(f"\nDisciplina: {disc}")

session, course_id = unoesc.abrir_curso(session, disc["dof"])
print(f"Course ID no Moodle: {course_id}")

# 4. Lista seções do curso
print("\n── Seções ──")
for s in unoesc.listar_secoes(session, course_id):
    print(f"  [{s['section_id']}] {s['nome']}")

# 5. Busca uma seção por data e lista suas atividades
secao = unoesc.buscar_secao(session, course_id, "27/04")
if secao:
    print(f"\n── Atividades em '{secao['nome']}' ──")
    for a in unoesc.listar_atividades(session, secao["section_id"]):
        print(f"  ({a['tipo']}) [{a['activity_id']}] {a['nome']}")
