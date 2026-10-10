"""Exemplo: listar encontros e consultar/lançar faltas no diário.

ATENÇÃO: o lançamento real altera o portal. Use dry_run=True primeiro.
Diários já publicados não aceitam edição (message da Secretaria).
"""
import unoesc

session = unoesc.open_session()

# 1) Diários do período (com DOF quando o plano está deferido)
diarios = unoesc.list_class_diaries(session, "2026/1")
for d in diarios:
    status = "bloqueado" if d["bloqueado"] else f"dof={d['dof']}"
    print(f"{d['codigo']} — {d['nome'][:50]} [{status}]")

# Escolha um diário editável (ex.: TCC I ainda aberto)
diario = next((d for d in diarios if d["dof"] and not d["bloqueado"]), None)
if not diario:
    raise SystemExit("Nenhum diário aberto neste período.")

dof = diario["dof"]
print(f"\nUsando: {diario['codigo']} dof={dof}")

# 2) Encontros do quadro
encontros = unoesc.list_meetings(session, dof)
for e in encontros:
    tipo = "in_person" if e["in_person"] else "não in_person" if e["in_person"] is False else "?"
    print(f"  aula={e['aula']}  {e['title']}  {e['data']}  ({tipo})")

if not encontros:
    raise SystemExit("Sem encontros no quadro.")

aula = encontros[0]["aula"]

# 3) Ler lista de presença / conteúdo
pres = unoesc.get_meeting_attendance(session, aula)
if pres["publicado"]:
    print("\nDiário publicado — não é possível editar faltas.")
    raise SystemExit(0)

print(f"\n{pres['discipline']}")
print(f"Conteúdo: {(pres.get('content') or '')[:80]}...")
print(f"Alunos: {len(pres['alunos'])}")
for a in pres["alunos"][:5]:
    print(f"  {a['ra']}  faltas={a['faltas']}  {a['nome'][:40]}")

# 4) Simular lançamento (não grava)
#    Marca 1 falta no primeiro aluno; zera os demais
primeiro = pres["alunos"][0]["ra"]
sim = unoesc.post_absences(
    session,
    aula,
    absentees={primeiro: 1},
    clear_others=True,
    dry_run=True,
)
print(f"\ndry_run alterados={len(sim['alterados'])} desconhecidos={sim.get('desconhecidos')}")

# 5) Para gravar de verdade, remova dry_run:
# unoesc.post_absences(session, aula, absentees={"412507": 2}, clear_others=True)
# ou só conteúdo:
# unoesc.save_meeting_attendance(session, aula, content="Aula sobre X...")
