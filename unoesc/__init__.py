"""
unoesc-tools — Portal de Ensino UNOESC + Moodle ON

Uso rápido:
    import unoesc
    session = unoesc.abrir_sessao()

Ou importe módulos individualmente:
    from unoesc import portal, moodle, grades, quiz_export
"""
from .auth   import abrir_sessao
from .portal import (
    listar_disciplinas,
    buscar_disciplina,
    listar_diarios,
    abrir_diario,
    listar_planos_ensino,
    consultar_notas,
    lista_presenca,
    lista_estudantes_a2,
    listar_alunos_para_mensagem,
    enviar_mensagem_alunos,
    enviar_notificacao_on,
    listar_ocorrencias,
    relatorio_perfil,
    relatorio_telefones,
    relatorio_assinaturas,
    quadro_horarios,
    importar_notas_diario,
    listar_avaliacoes_diario,
    extrair_mapa_alunos_diario,
    lancar_notas_diario,
)
from .moodle import (
    abrir_curso,
    listar_secoes,
    buscar_secao,
    listar_atividades,
    buscar_atividade,
    ver_tarefa,
    ver_quiz,
    ver_forum,
    baixar_recurso,
)
from .quiz_export import (
    listar_questoes_categoria,
    listar_categorias_banco,
    obter_questao,
    analisar_quiz,
    extrair_questionario,
    extrair_banco_questoes,
    exportar_questionario_docx,
    exportar_questionario_pdf,
    exportar_questionario,
    exportar_questionario_disciplina,
    exportar_banco_questoes,
    exportar_banco_questoes_disciplina,
)
from .grades import (
    listar_itens_avaliacao,
    exportar_notas_csv,
    exportar_notas_excel,
    exportar_notas_tarefa,
    exportar_notas_quiz,
    exportar_notas_para_portal,
)

__all__ = [
    # auth
    "abrir_sessao",
    # portal
    "listar_disciplinas", "buscar_disciplina",
    "listar_diarios", "abrir_diario",
    "listar_planos_ensino",
    "consultar_notas", "lista_presenca", "lista_estudantes_a2",
    "listar_alunos_para_mensagem", "enviar_mensagem_alunos", "enviar_notificacao_on",
    "listar_ocorrencias",
    "relatorio_perfil", "relatorio_telefones", "relatorio_assinaturas",
    "quadro_horarios",
    # moodle
    "abrir_curso", "listar_secoes", "buscar_secao",
    "listar_atividades", "buscar_atividade",
    "ver_tarefa", "ver_quiz", "ver_forum", "baixar_recurso",
    # grades
    "listar_itens_avaliacao",
    "exportar_notas_csv", "exportar_notas_excel",
    "exportar_notas_tarefa", "exportar_notas_quiz",
    "exportar_notas_para_portal",
    # quiz export
    "listar_questoes_categoria", "listar_categorias_banco", "obter_questao", "analisar_quiz",
    "extrair_questionario", "extrair_banco_questoes",
    "exportar_questionario_docx", "exportar_questionario_pdf",
    "exportar_questionario", "exportar_questionario_disciplina",
    "exportar_banco_questoes", "exportar_banco_questoes_disciplina",
    # portal — importação e lançamento de notas
    "listar_avaliacoes_diario",
    "importar_notas_diario",
    "extrair_mapa_alunos_diario",
    "lancar_notas_diario",
]
