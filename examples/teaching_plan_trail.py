"""Exemplo: ler plano de ensino e comparar com a trilha do Moodle.

Somente leitura — não cria/altera seções nem atividades.
"""
import unoesc

session = unoesc.open_session()

# 1) Planos do período
for p in unoesc.list_teaching_plans(session, "2026/2"):
    print(f"{p['codigo']} dof={p['dof']}  [{p['situacao']}]  {p['nome'][:50]}")

# 2) Plano completo (ex.: Banco de Dados EAD 2026/2)
dof = "1414934"
plano = unoesc.get_teaching_plan(session, dof)
print(f"\n{plano['discipline']}")
print(f"Objetivo: {plano['general_objective'][:120]}...")
print(f"Unidades: {len(plano['units'])} | Cronograma: {len(plano['schedule'])}")
print(f"Bibliografias: {len(plano['bibliographies'])} | Avaliações: {len(plano['assessments'])}")

for u in plano["units"]:
    print(f"  U{u['ordem']} {u['nome']}")

for c in plano["schedule"]:
    print(f"  #{c['ordem']} {c['tipo']:20} {c['dia'][:30]:30} {(c['content'] or '')[:50]}")

# 3) Estrutura atual no Moodle (sem mexer em nada)
ms, course_id = unoesc.open_course(session, dof)
estrutura = unoesc.get_course_structure(ms, course_id, include_activities=False)
print(f"\nMoodle course={course_id} pattern={estrutura['pattern']} secoes={estrutura['n_sections']}")
for s in estrutura["sections"]:
    print(f"  [{s['papel']:12}] {s['nome'][:60]}")

# 4) Resumo plano × trilha
analise = unoesc.analyze_plan_trail(session, dof, include_activities=False)
print("\nResumo:", analise["resumo"])
