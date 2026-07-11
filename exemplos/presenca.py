"""Exemplo: listar encontros e consultar/lançar faltas no diário.

ATENÇÃO: o lançamento real altera o portal. Use dry_run=True primeiro.
Diários já publicados não aceitam edição (mensagem da Secretaria).
"""
import unoesc

session = unoesc.abrir_sessao()

# 1) Diários do período (com DOF quando o plano está deferido)
diarios = unoesc.listar_diarios(session, "2026/1")
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
encontros = unoesc.listar_encontros(session, dof)
for e in encontros:
    tipo = "presencial" if e["presencial"] else "não presencial" if e["presencial"] is False else "?"
    print(f"  aula={e['aula']}  {e['titulo']}  {e['data']}  ({tipo})")

if not encontros:
    raise SystemExit("Sem encontros no quadro.")

aula = encontros[0]["aula"]

# 3) Ler lista de presença / conteúdo
pres = unoesc.obter_presencas_encontro(session, aula)
if pres["publicado"]:
    print("\nDiário publicado — não é possível editar faltas.")
    raise SystemExit(0)

print(f"\n{pres['disciplina']}")
print(f"Conteúdo: {(pres.get('conteudo') or '')[:80]}...")
print(f"Alunos: {len(pres['alunos'])}")
for a in pres["alunos"][:5]:
    print(f"  {a['ra']}  faltas={a['faltas']}  {a['nome'][:40]}")

# 4) Simular lançamento (não grava)
#    Marca 1 falta no primeiro aluno; zera os demais
primeiro = pres["alunos"][0]["ra"]
sim = unoesc.lancar_faltas(
    session,
    aula,
    faltosos={primeiro: 1},
    zerar_demais=True,
    dry_run=True,
)
print(f"\ndry_run alterados={len(sim['alterados'])} desconhecidos={sim.get('desconhecidos')}")

# 5) Para gravar de verdade, remova dry_run:
# unoesc.lancar_faltas(session, aula, faltosos={"412507": 2}, zerar_demais=True)
# ou só conteúdo:
# unoesc.salvar_presencas_encontro(session, aula, conteudo="Aula sobre X...")
