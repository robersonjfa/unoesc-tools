"""
Exportação de notas do Moodle ON UNOESC.

Suporta exportação de notas de todo o curso (CSV ou Excel),
de tarefas específicas (assign) e de questionários (quiz).
"""
import re
import os
import csv
import io
from bs4 import BeautifulSoup
from requests import Session

MOODLE_BASE = "https://on.unoesc.edu.br"


def _soup(html):
    return BeautifulSoup(html, "html.parser")


def _form_export(session, course_id, formato="txt"):
    """Retorna (form_soup, sesskey, todos_item_ids) da página de exportação."""
    resp = session.get(f"{MOODLE_BASE}/grade/export/{formato}/index.php?id={course_id}")
    soup = _soup(resp.text)
    form = soup.find("form", action=re.compile("export.php"))
    if not form:
        raise RuntimeError("Formulário de exportação não encontrado.")
    sesskey = form.find("input", {"name": "sesskey"})["value"]
    item_ids = []
    for cb in form.find_all("input", {"type": "checkbox", "name": re.compile("itemids")}):
        m = re.search(r"\[(\d+)\]", cb["name"])
        if m:
            item_ids.append(m.group(1))
    return form, sesskey, item_ids


def listar_itens_avaliacao(session: Session, course_id: str) -> list[dict]:
    """Lista todas as atividades avaliadas do curso com seus IDs.

    Returns:
        list[dict]: [{item_id, nome}, ...]
          O item_id é usado para filtrar a exportação.
          O último item é sempre 'Total do curso'.
    """
    resp = session.get(f"{MOODLE_BASE}/grade/export/txt/index.php?id={course_id}")
    soup = _soup(resp.text)
    form = soup.find("form", action=re.compile("export.php"))
    if not form:
        return []
    itens = []
    for cb in form.find_all("input", {"type": "checkbox", "name": re.compile("itemids")}):
        m = re.search(r"\[(\d+)\]", cb["name"])
        if not m:
            continue
        item_id = m.group(1)
        label = cb.find_next_sibling("label") or cb.find_next("label")
        nome = label.get_text(strip=True) if label else item_id
        itens.append({"item_id": item_id, "nome": nome})
    return itens


def exportar_notas_csv(session: Session, course_id: str, item_ids: list[str] | None = None, destino: str | None = None, separador: str = "comma") -> tuple[str, list[dict]]:
    """Exporta notas do curso como CSV.

    Args:
        item_ids:  list de item_ids a incluir. None = todos.
        destino:   caminho do arquivo. None = ~/Downloads/notas_<course_id>.csv
        separador: 'comma' | 'tab' | 'semicolon' | 'colon'

    Returns:
        (caminho_arquivo, list[dict]): arquivo salvo e dados como lista de dicts.
        Cada dict tem: Nome, Sobrenome, Endereço de e-mail, e uma coluna por atividade.
    """
    form, sesskey, todos_ids = _form_export(session, course_id, "txt")
    selecionados = item_ids if item_ids else todos_ids

    data = {
        "mform_isexpanded_id_gradeitems": "1",
        "checkbox_controller1": "1",
        "mform_isexpanded_id_options": "0",
        "id": course_id,
        "sesskey": sesskey,
        "_qf__grade_export_form": "1",
        "export_onlyactive": "1",
        "display[real]": "1",
        "separator": separador,
        "decimals": "2",
        "submitbutton": "Download",
    }
    for iid in selecionados:
        data[f"itemids[{iid}]"] = "1"

    resp_dl = session.post(f"{MOODLE_BASE}/grade/export/txt/export.php", data=data)

    if destino is None:
        destino = os.path.expanduser(f"~/Downloads/notas_{course_id}.csv")

    with open(destino, "w", encoding="utf-8") as f:
        f.write(resp_dl.text)

    sep_char = {"comma": ",", "tab": "\t", "semicolon": ";", "colon": ":"}.get(separador, ",")
    dados = list(csv.DictReader(io.StringIO(resp_dl.text), delimiter=sep_char))

    print(f"Notas exportadas: {len(dados)} alunos → {destino}")
    return destino, dados


def exportar_notas_excel(session: Session, course_id: str, item_ids: list[str] | None = None, destino: str | None = None) -> str:
    """Exporta notas do curso como arquivo Excel (.xlsx).

    Args:
        item_ids: list de item_ids a incluir. None = todos.
        destino:  caminho do arquivo. None = ~/Downloads/notas_<course_id>.xlsx

    Returns:
        Caminho do arquivo salvo.
    """
    form, sesskey, todos_ids = _form_export(session, course_id, "xls")
    selecionados = item_ids if item_ids else todos_ids

    data = {
        "mform_isexpanded_id_gradeitems": "1",
        "checkbox_controller1": "1",
        "mform_isexpanded_id_options": "0",
        "id": course_id,
        "sesskey": sesskey,
        "_qf__grade_export_form": "1",
        "export_onlyactive": "1",
        "display[real]": "1",
        "decimals": "2",
        "submitbutton": "Download",
    }
    for iid in selecionados:
        data[f"itemids[{iid}]"] = "1"

    resp_dl = session.post(f"{MOODLE_BASE}/grade/export/xls/export.php", data=data)

    if destino is None:
        destino = os.path.expanduser(f"~/Downloads/notas_{course_id}.xlsx")

    with open(destino, "wb") as f:
        f.write(resp_dl.content)

    print(f"Excel salvo em: {destino}")
    return destino


def exportar_notas_tarefa(session: Session, assign_id: str) -> list[dict]:
    """Retorna notas e status de entrega de uma tarefa (assign).

    Args:
        assign_id: activity_id da tarefa (campo 'activity_id' de listar_atividades).

    Returns:
        list[dict]: [{aluno, nota, status, data_entrega}, ...]
    """
    resp = session.get(f"{MOODLE_BASE}/mod/assign/view.php?id={assign_id}&action=grading")
    soup = _soup(resp.text)
    linhas = []
    for tr in soup.find_all("tr", class_=re.compile("student|user")):
        cols = tr.find_all("td")
        if len(cols) < 3:
            continue
        aluno  = tr.find(class_=re.compile("fullname|username"))
        nota   = tr.find(class_=re.compile("grade"))
        status = tr.find(class_=re.compile("status|submissionstatus"))
        data   = tr.find(class_=re.compile("timemodified|date"))
        linhas.append({
            "aluno":        aluno.get_text(strip=True) if aluno else cols[0].get_text(strip=True),
            "nota":         nota.get_text(strip=True) if nota else "-",
            "status":       status.get_text(strip=True) if status else "-",
            "data_entrega": data.get_text(strip=True) if data else "-",
        })
    return linhas


def exportar_notas_para_portal(
    session: Session,
    course_id: str,
    item_id: str,
    nome_atividade: str | None = None,
    tipo: str = "Tarefa",
    destino: str | None = None,
) -> tuple[str, list[dict]]:
    """Exporta notas de uma atividade do Moodle no formato CSV de importação do Portal UNOESC.

    O CSV gerado pode ser enviado via importar_notas_diario() ou importado manualmente
    no diário de classe do portal.

    Args:
        item_id:        ID da atividade (obtido via listar_itens_avaliacao).
        nome_atividade: Nome da atividade no CSV. None = usa o nome do Moodle.
        tipo:           Tipo de atividade ('Tarefa', 'Quiz', etc.).
        destino:        Caminho do arquivo. None = ~/Downloads/portal_<slug>.csv

    Returns:
        (caminho_arquivo, list[dict]): cada dict tem
        {Usuário, Atividade, Avaliação, Tipo de atividade}
    """
    if nome_atividade is None:
        itens = listar_itens_avaliacao(session, course_id)
        item = next((i for i in itens if i["item_id"] == item_id), None)
        nome_atividade = item["nome"] if item else item_id

    _, moodle_dados = exportar_notas_csv(session, course_id, item_ids=[item_id], separador="comma")

    # Colunas que não são notas no CSV do Moodle
    PREFIXOS_META = {
        "nome", "sobrenome", "número de identificação", "instituição",
        "departamento", "endereço de e-mail", "email address",
        "first name", "surname", "id number", "institution", "department",
        "último download realizado neste curso.",
    }

    # Colunas de nota têm o formato "Tipo:\xa0NOME (Real)" — achamos pela busca no nome
    def _col_nota(keys: list[str]) -> str | None:
        # 1. Procura coluna cujo nome contém nome_atividade (sem considerar prefixo/sufixo)
        alvo = nome_atividade.lower()
        for k in keys:
            if alvo in k.lower():
                return k
        # 2. Fallback: primeira coluna que não é meta e não é "Total do curso"
        for k in keys:
            kl = k.lower()
            if kl not in PREFIXOS_META and "total do curso" not in kl and "last downloaded" not in kl:
                return k
        return None

    resultado = []
    for row in moodle_dados:
        keys = list(row.keys())
        nome_col  = next((k for k in keys if k.lower() in ("nome", "first name")), keys[0] if keys else "")
        sobre_col = next((k for k in keys if k.lower() in ("sobrenome", "surname")), keys[1] if len(keys) > 1 else "")
        nota_col  = _col_nota(keys)

        nome_completo = f"{row.get(nome_col, '')} {row.get(sobre_col, '')}".strip().upper()
        nota_raw = row.get(nota_col, "0") if nota_col else "0"
        try:
            nota_fmt = f"{float(nota_raw):.2f}"
        except (ValueError, TypeError):
            nota_fmt = "0.00"

        resultado.append({
            "Usuário": nome_completo,
            "Atividade": nome_atividade.upper(),
            "Avaliação": nota_fmt,
            "Tipo de atividade": tipo,
        })

    if destino is None:
        slug = re.sub(r"\W+", "_", nome_atividade).strip("_").lower()
        destino = os.path.expanduser(f"~/Downloads/portal_{slug}.csv")

    with open(destino, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Usuário", "Atividade", "Avaliação", "Tipo de atividade"])
        writer.writeheader()
        writer.writerows(resultado)

    print(f"CSV portal gerado: {len(resultado)} alunos → {destino}")
    return destino, resultado


def exportar_notas_quiz(session: Session, quiz_id: str) -> list[dict]:
    """Retorna relatório de tentativas e notas de um questionário (quiz).

    Args:
        quiz_id: activity_id do quiz (campo 'activity_id' de listar_atividades).

    Returns:
        list[dict] com colunas: Nome/Sobrenome, E-mail, Situação,
        Iniciado, Completo, Duração (e nota quando disponível).
    """
    resp = session.get(f"{MOODLE_BASE}/mod/quiz/report.php?id={quiz_id}&mode=overview")
    soup = _soup(resp.text)
    table = (
        soup.find("table", id=re.compile("attempts"))
        or soup.find("table", class_=re.compile("generaltable"))
    )
    if not table:
        return []
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    linhas = []
    for tr in table.find_all("tr")[1:]:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cols:
            linhas.append(dict(zip(headers, cols)) if headers else cols)
    return linhas
