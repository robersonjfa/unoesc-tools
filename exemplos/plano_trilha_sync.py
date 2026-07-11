"""Preview da sincronização plano → trilha Moodle (somente dry_run).

Não cria nem altera seções/atividades enquanto dry_run=True (padrão).
"""
import unoesc

session = unoesc.abrir_sessao()

# Prog IV (presencial) — datas do plano vs seções Aula N
DOF = "1416625"

plano = unoesc.planejar_sincronizacao_trilha(
    session, DOF, incluir_atividades=True
)
print(f"padrao={plano['padrao']} course={plano['course_id']}")
print(f"secoes criar={len(plano['secoes_criar'])} ignorar={len(plano['secoes_ignorar'])}")
for s in plano["secoes_criar"][:10]:
    print(f"  + [{s['papel']}] {s['nome']}")
print(f"atividades criar={len(plano['atividades_criar'])} ignorar={len(plano['atividades_ignorar'])}")
for a in plano["atividades_criar"][:8]:
    print(f"  + {a['tipo']:8} @ {a['secao_nome'][:30]:30} {a['nome'][:40]}")

# Sync simulada (nenhum POST de mutação)
resultado = unoesc.sincronizar_trilha_do_plano(
    session,
    DOF,
    criar_secoes=True,
    criar_atividades=True,
    dry_run=True,  # padrão — mantenha True até revisar o preview
)
print(f"\ndry_run={resultado['dry_run']} sucesso={resultado['sucesso']}")
print(f"criaria secoes={len(resultado['criados'])} atividades={len(resultado['atividades_criadas'])}")

# Para gravar de verdade (CUIDADO):
# unoesc.sincronizar_trilha_do_plano(session, DOF, criar_secoes=True, criar_atividades=False, dry_run=False)
