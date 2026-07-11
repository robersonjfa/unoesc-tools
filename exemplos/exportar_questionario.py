"""
Exemplo: exportar questionário Moodle para DOCX e PDF.

Ajuste os parâmetros abaixo para sua disciplina/atividade.
"""
import unoesc

# ── Configuração ──────────────────────────────────────────────────────────────

DISCIPLINA     = "10276/EAD54-12"   # ou "Banco de Dados"
SECAO          = "Semana 7"         # substring da seção
ATIVIDADE      = "Prova Objetiva"   # substring do questionário (tipo quiz)
INCLUIR_GABARITO = True

# ── Exportação ────────────────────────────────────────────────────────────────

session = unoesc.abrir_sessao()

resultado = unoesc.exportar_questionario_disciplina(
    session,
    disciplina_termo=DISCIPLINA,
    secao_termo=SECAO,
    atividade_termo=ATIVIDADE,
    formatos=("docx", "pdf"),
    incluir_gabarito=INCLUIR_GABARITO,
)

print("\n── Resultado ──")
print(f"Questões exportadas: {resultado['dados']['total_questoes']}")
if resultado.get("docx"):
    print(f"DOCX: {resultado['docx']}")
if resultado.get("pdf"):
    print(f"PDF:  {resultado['pdf']}")
