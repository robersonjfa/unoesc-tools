"""
Exemplo: exportar questionário Moodle para DOCX e PDF.

Ajuste os parâmetros abaixo para sua discipline/atividade.
"""
import unoesc

# ── Configuração ──────────────────────────────────────────────────────────────

DISCIPLINA     = "10276/EAD54-12"   # ou "Banco de Dados"
SECAO          = "Semana 7"         # substring da seção
ATIVIDADE      = "Prova Objetiva"   # substring do questionário (tipo quiz)
INCLUIR_GABARITO = True

# ── Exportação ────────────────────────────────────────────────────────────────

session = unoesc.open_session()

resultado = unoesc.export_discipline_quiz(
    session,
    discipline_query=DISCIPLINA,
    section_query=SECAO,
    activity_query=ATIVIDADE,
    formats=("docx", "pdf"),
    include_answer_key=INCLUIR_GABARITO,
)

print("\n── Resultado ──")
print(f"Questões exportadas: {resultado['dados']['total_questoes']}")
if resultado.get("docx"):
    print(f"DOCX: {resultado['docx']}")
if resultado.get("pdf"):
    print(f"PDF:  {resultado['pdf']}")
