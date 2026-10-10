"""Preview da sincronização plano → trilha Moodle (somente dry_run).

Não cria nem altera seções/atividades enquanto dry_run=True (padrão).
"""
import unoesc

session = unoesc.open_session()

# Prog IV (in_person) — datas do plano vs seções Aula N
DOF = "1416625"

plano = unoesc.plan_trail_sync(
    session, DOF, include_activities=True
)
print(f"pattern={plano['pattern']} course={plano['course_id']}")
print(f"secoes criar={len(plano['sections_to_create'])} ignorar={len(plano['sections_to_skip'])}")
for s in plano["sections_to_create"][:10]:
    print(f"  + [{s['papel']}] {s['nome']}")
print(f"atividades criar={len(plano['activities_to_create'])} ignorar={len(plano['activities_to_skip'])}")
for a in plano["activities_to_create"][:8]:
    print(f"  + {a['tipo']:8} @ {a['section_name'][:30]:30} {a['nome'][:40]}")

# Sync simulada (nenhum POST de mutação)
resultado = unoesc.sync_trail_from_plan(
    session,
    DOF,
    create_sections=True,
    create_activities=True,
    dry_run=True,  # padrão — mantenha True até revisar o preview
)
print(f"\ndry_run={resultado['dry_run']} success={resultado['success']}")
print(f"criaria secoes={len(resultado['created'])} atividades={len(resultado['activities_created'])}")

# Para gravar de verdade (CUIDADO):
# unoesc.sync_trail_from_plan(session, DOF, create_sections=True, create_activities=False, dry_run=False)
