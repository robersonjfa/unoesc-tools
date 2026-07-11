"""
Exemplo: importar notas do Moodle para o diário do Portal UNOESC.

Fluxo:
  1. Abre sessão no portal + Moodle
  2. Exporta notas da atividade do Moodle no formato CSV do Portal
  3. Tenta importar via CSV (endpoint multipart)
  4. Se o CSV falhar (problema com Java multipart), lança nota a nota via saveNota

Parâmetros configuráveis abaixo — ajuste para a sua disciplina.
"""
import unoesc

# ── Configuração ──────────────────────────────────────────────────────────────

DOF            = "1410552"   # código DOF da disciplina
ITEM_ID_MOODLE = "5917"      # item_id da atividade no Moodle (listar_itens_avaliacao)
NOME_ATIVIDADE = "ATIVIDADE AVALIATIVA 3"
AVALIACAO_SEQ  = 3           # sequência da avaliação no portal (1=A1/01, 2=A1/02, 3=A1/03)
COD_TIPO_NOTA  = "24"        # codTipoNota (visto nos spans do HTML do diário)

# ── Início ────────────────────────────────────────────────────────────────────

session = unoesc.abrir_sessao()
session, course_id = unoesc.abrir_curso(session, DOF)

print(f"Curso Moodle: {course_id}")

# 1. Ver avaliações disponíveis no diário
print("\n── Avaliações no diário ──")
avaliacoes = unoesc.listar_avaliacoes_diario(session, DOF)
for av in avaliacoes:
    print(f"  {av['nome']}  (codTipoNota={av['cod_tipo_nota']} avaliacao={av['avaliacao']} nota={av['nota']})")

# 2. Exporta notas do Moodle no formato CSV do Portal
print(f"\n── Exportando notas do Moodle (item_id={ITEM_ID_MOODLE}) ──")
csv_path, dados_moodle = unoesc.exportar_notas_para_portal(
    session, course_id,
    item_id=ITEM_ID_MOODLE,
    nome_atividade=NOME_ATIVIDADE,
)
print(f"CSV gerado em: {csv_path}")
print(f"Primeiros 3 registros: {dados_moodle[:3]}")

# 3. Tenta importação via CSV (pode falhar em servidores Java antigos sem suporte multipart)
print("\n── Tentando importação via CSV ──")
resultado_csv = unoesc.importar_notas_diario(
    session,
    dof=DOF,
    csv_path=csv_path,
    avaliacao=AVALIACAO_SEQ,
)
print(f"Status: {resultado_csv['status_code']}")
print(f"Mensagem: {resultado_csv['mensagem']}")
print(f"Avaliação usada: {resultado_csv['avaliacao']}")

# 4. Se o import via CSV não funcionar (ou como alternativa direta),
#    lança nota por nota via saveNota usando o RA do Moodle como chave.
#
#    O e-mail do aluno no Moodle tem formato RA@unoesc.edu.br, mas o CSV
#    exportado por exportar_notas_para_portal() usa o nome completo.
#    Para usar RA como chave, exporte via exportar_notas_csv() e extraia
#    o RA do campo "Endereço de e-mail".

print("\n── Mapa de alunos no diário ──")
alunos_diario = unoesc.extrair_mapa_alunos_diario(session, DOF)
print(f"{len(alunos_diario)} alunos encontrados no diário.")
for a in alunos_diario[:3]:
    print(f"  RA={a['ra']}  nome={a['nome']}  cod_adm={a['cod_adm']}")

# Monta dict {nome_completo: nota} a partir do CSV do Portal
notas_por_nome = {d["Usuário"]: float(d["Avaliação"]) for d in dados_moodle}

print(f"\n── Lançando {len(notas_por_nome)} notas via saveNota ──")
resultado = unoesc.lancar_notas_diario(
    session,
    dof=DOF,
    notas=notas_por_nome,
    avaliacao=AVALIACAO_SEQ,
    cod_tipo_nota=COD_TIPO_NOTA,
)

print(f"\nResultado final:")
print(f"  Total:            {resultado['total']}")
print(f"  Sucesso:          {resultado['sucesso']}")
print(f"  Falha:            {resultado['falha']}")
print(f"  Não encontrados:  {len(resultado['nao_encontrados'])}")

if resultado["nao_encontrados"]:
    print(f"\nAlunos não encontrados no diário:")
    for nome in resultado["nao_encontrados"]:
        print(f"  - {nome}")

print("\nDetalhes (primeiros 5):")
for r in resultado["resultados"][:5]:
    status = "OK" if r["sucesso"] else "FALHA"
    print(f"  [{status}] {r['nome']} (RA={r['ra']}) nota={r['nota']}  cn={r['cn']}  resp={r['resposta'][:60]!r}")
