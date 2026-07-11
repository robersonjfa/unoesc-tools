"""
Exemplo: exportação de notas de diversas formas.
"""
import unoesc

session = unoesc.abrir_sessao()

disc = unoesc.buscar_disciplina(session, "Banco de Dados")  # ajuste para sua disciplina
session, course_id = unoesc.abrir_curso(session, disc["dof"])

# 1. Ver quais atividades têm nota
print("── Itens avaliados ──")
for item in unoesc.listar_itens_avaliacao(session, course_id):
    print(f"  [{item['item_id']}] {item['nome']}")

# 2. Exportar todas as notas como CSV
caminho, dados = unoesc.exportar_notas_csv(session, course_id)
print(f"\nCSV com {len(dados)} alunos salvo em: {caminho}")

# 3. Exportar apenas atividades específicas (ex: só as tarefas)
# unoesc.exportar_notas_csv(session, course_id, item_ids=["11070", "11072", "11073"])

# 4. Exportar como Excel
unoesc.exportar_notas_excel(session, course_id)

# 5. Notas de uma tarefa específica (assign)
print("\n── Notas da tarefa 'Modelagem e Normalização' ──")
notas = unoesc.exportar_notas_tarefa(session, "29328")
for n in notas[:5]:
    print(f"  {n['aluno']}: {n['nota']} | {n['status']}")

# 6. Relatório de um questionário (quiz)
print("\n── Quiz: Times e ideias de projeto ──")
tentativas = unoesc.exportar_notas_quiz(session, "43724")
for t in tentativas[:5]:
    # Acessa as colunas pelo nome limpo
    nome = list(t.values())[1] if len(t) > 1 else str(t)
    print(f"  {nome}")
