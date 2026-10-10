"""Atualizar datas de uma atividade Moodle (dry_run por padrão).

Padrão inspirado no py-moodle ``update_generic_module``:
GET modedit → preserva form → aplica só os campos pedidos.
"""
import unoesc

session = unoesc.open_session()

# Mineração de Dados 2026/2 — "Atividade não avaliativa 02" (cmid conhecido)
DOF = "1414974"
ACTIVITY_ID = "77069"

ms, course_id = unoesc.open_course(session, DOF)
print(f"course_id={course_id}")

# Preview: corrige datas 2025 → alinhadas ao período do plano (exemplo)
resultado = unoesc.update_activity(
    ms,
    ACTIVITY_ID,
    options={
        "allowsubmissionsfromdate": "27/07/2026 07:00",
        "duedate": "04/10/2026 23:59",
        "cutoffdate": "04/10/2026 23:59",
    },
    dry_run=True,  # padrão — nenhum POST
)
print(f"dry_run={resultado['dry_run']} success={resultado['success']}")
print(f"message={resultado.get('message')}")
for campo, diff in (resultado.get("changed_fields") or {}).items():
    print(f"  {campo}: {diff['de']!r} → {diff['para']!r}")

# Para gravar de verdade (CUIDADO):
# unoesc.update_activity(ms, ACTIVITY_ID, options={...}, dry_run=False)
