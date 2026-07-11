"""Exemplo: ler plano de ensino e comparar com a trilha do Moodle.

Somente leitura — não cria/altera seções nem atividades.
"""
import unoesc

session = unoesc.abrir_sessao()

# 1) Planos do período
for p in unoesc.listar_planos_ensino(session, "2026/2"):
    print(f"{p['codigo']} dof={p['dof']}  [{p['situacao']}]  {p['nome'][:50]}")

# 2) Plano completo (ex.: Banco de Dados EAD 2026/2)
dof = "1414934"
plano = unoesc.obter_plano_ensino(session, dof)
print(f"\n{plano['disciplina']}")
print(f"Objetivo: {plano['objetivo_geral'][:120]}...")
print(f"Unidades: {len(plano['unidades'])} | Cronograma: {len(plano['cronograma'])}")
print(f"Bibliografias: {len(plano['bibliografias'])} | Avaliações: {len(plano['avaliacoes'])}")

for u in plano["unidades"]:
    print(f"  U{u['ordem']} {u['nome']}")

for c in plano["cronograma"]:
    print(f"  #{c['ordem']} {c['tipo']:20} {c['dia'][:30]:30} {(c['conteudo'] or '')[:50]}")

# 3) Estrutura atual no Moodle (sem mexer em nada)
ms, course_id = unoesc.abrir_curso(session, dof)
estrutura = unoesc.obter_estrutura_curso(ms, course_id, incluir_atividades=False)
print(f"\nMoodle course={course_id} padrao={estrutura['padrao']} secoes={estrutura['n_secoes']}")
for s in estrutura["secoes"]:
    print(f"  [{s['papel']:12}] {s['nome'][:60]}")

# 4) Resumo plano × trilha
analise = unoesc.analisar_plano_trilha(session, dof, incluir_atividades=False)
print("\nResumo:", analise["resumo"])
