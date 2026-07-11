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
    listar_encontros,
    adicionar_encontro,
    remover_encontro,
    definir_encontro_presencial,
    obter_presencas_encontro,
    salvar_presencas_encontro,
    lancar_faltas,
    listar_planos_ensino,
    obter_plano_ensino,
    listar_cronograma_plano,
    listar_unidades_plano,
    listar_bibliografias_plano,
    listar_avaliacoes_plano,
    analisar_plano_trilha,
    planejar_secoes_do_plano,
    planejar_atividades_do_plano,
    planejar_sincronizacao_trilha,
    sincronizar_trilha_do_plano,
    consultar_notas,
    lista_presenca,
    lista_estudantes_a2,
    listar_alunos_para_mensagem,
    listar_turmas_mensagem,
    buscar_alunos_mensagem,
    enviar_mensagem_alunos,
    enviar_mensagem_turmas,
    enviar_notificacao_on,
    comunicar_estudantes,
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
    classificar_secao,
    obter_estrutura_curso,
    criar_secao,
    atualizar_secao,
    criar_atividade,
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
    "listar_encontros", "adicionar_encontro", "remover_encontro",
    "definir_encontro_presencial",
    "obter_presencas_encontro", "salvar_presencas_encontro", "lancar_faltas",
    "listar_planos_ensino",
    "obter_plano_ensino",
    "listar_cronograma_plano", "listar_unidades_plano",
    "listar_bibliografias_plano", "listar_avaliacoes_plano",
    "analisar_plano_trilha",
    "planejar_secoes_do_plano", "planejar_atividades_do_plano",
    "planejar_sincronizacao_trilha", "sincronizar_trilha_do_plano",
    "consultar_notas", "lista_presenca", "lista_estudantes_a2",
    "listar_alunos_para_mensagem", "listar_turmas_mensagem", "buscar_alunos_mensagem",
    "enviar_mensagem_alunos", "enviar_mensagem_turmas",
    "enviar_notificacao_on", "comunicar_estudantes",
    "listar_ocorrencias",
    "relatorio_perfil", "relatorio_telefones", "relatorio_assinaturas",
    "quadro_horarios",
    # moodle
    "abrir_curso", "listar_secoes", "buscar_secao",
    "listar_atividades", "buscar_atividade",
    "classificar_secao", "obter_estrutura_curso",
    "criar_secao", "atualizar_secao", "criar_atividade",
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
