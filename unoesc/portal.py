"""
Funções para o Portal de Ensino UNOESC (acad.unoesc.edu.br).

Cobre: disciplinas, diário de classe, plano de ensino, notas,
listas de presença, ocorrências, mensagens, horários.
"""
import os
import re
from bs4 import BeautifulSoup
from requests import Session
from .auth import BASE_URL

MODULOS = {
    "aula_online":           "/portal/modules/prof/aulaOnlineMoodlerooms.jspa?t=1",
    "avaliacoes":            "/portal/modules/prof/avaliacao.jspa",
    "ocorrencias":           "/portal/modules/prof/alunoCursoObservacao.jspa",
    "mensagem_alunos":       "/portal/modules/prof/sendmail.jspa",
    "mensagem_selecionar":   "/portal/modules/prof/sendmail2.jspa",
    "mensagem_compor":       "/portal/modules/prof/sendmail3.jspa",
    "mensagem_formados":     "/portal/modules/prof/sendmailFormado.jspa?evt=formado",
    "mensagem_professores":  "/portal/modules/prof/sendmailprof.jspa",
    "notificacao_on":        "/portal/modules/prof/sendNotificationProfessor.jspa",
    "diario_classe":         "/portal/modules/prof/diarioClasse.jspa",
    "plano_ensino":          "/portal/modules/prof/planoEnsino.jspa",
    "parecer_diario":        "/portal/modules/prof/diarioClasseTramiteCoordenador.jspa",
    "parecer_plano":         "/portal/modules/prof/planoEnsinoCoordenadorAcessor.jspa",
    "plano_atividades":      "/portal/modules/prof/planoAtividades.jspa",
    "quadro_horarios":       "/portal/modules/prof/quadroHorariosProfessor.jspa",
    "consulta_notas":        "/portal/modules/prof/consnota.jspa",
    "lista_presenca_a1":     "/portal/modules/prof/alulistag2.jspa",
    "lista_estudantes_a2":   "/portal/modules/prof/alulistaexame.jspa",
    "relatorio_assinaturas": "/portal/modules/prof/aluassinat.jspa",
    "relatorio_perfil":      "/portal/modules/prof/aluperfil.jspa",
    "relatorio_telefones":   "/portal/modules/prof/alufone.jspa",
    "diario_aulas":          "/portal/modules/prof/diarioClasseAulas.jspa",
    "diario_notas":          "/portal/modules/prof/diarioClasseAvaliacoesNotas.jspa",
    "diario_arquivo":        "/portal/modules/prof/diarioClasseAvaliacoesArquivo.jspa",
}


# ── Utilitários internos ──────────────────────────────────────────────────────

def _soup(html):
    return BeautifulSoup(html, "html.parser")

def _get(session, modulo, params=None):
    path = MODULOS.get(modulo, modulo)
    return session.get(f"{BASE_URL}{path}", params=params, allow_redirects=True)

def _post(session, modulo, data):
    path = MODULOS.get(modulo, modulo)
    return session.post(f"{BASE_URL}{path}", data=data, allow_redirects=True)

def _tabela(soup, index=0):
    """Converte tabela HTML em lista de dicts. Usa <th> como chaves."""
    tables = soup.find_all("table")
    if not tables or index >= len(tables):
        return []
    table = tables[index]
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    rows = []
    for tr in table.find_all("tr")[1:]:
        cols = [re.sub(r"\s+", " ", td.get_text()).strip() for td in tr.find_all("td")]
        if cols:
            rows.append(dict(zip(headers, cols)) if headers else cols)
    return rows


# ── Disciplinas ───────────────────────────────────────────────────────────────

def listar_disciplinas(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Lista disciplinas do professor com acesso ao Moodle.

    Args:
        ano_periodo: ex. "2026/1". None = período atual.

    Returns:
        list[dict]: [{codigo, nome, dof}, ...]
          - dof: identificador usado para abrir o curso no Moodle
    """
    params = {"selAnoPeriodo": ano_periodo} if ano_periodo else None
    resp = _get(session, "aula_online", params)
    rows = re.findall(
        r'<a class="link-moodle"\s+data-dof="(\d+)"[^>]*>\s*(.*?)\s*</a>',
        resp.text, re.DOTALL,
    )
    result = []
    for dof, texto in rows:
        texto = re.sub(r"\s+", " ", texto).strip()
        partes = texto.split(" - ", 1)
        result.append({
            "codigo": partes[0].strip(),
            "nome":   partes[1].strip() if len(partes) > 1 else texto,
            "dof":    dof,
        })
    return result


def buscar_disciplina(session: Session, termo: str) -> dict | None:
    """Busca disciplina por código ou nome parcial (case-insensitive).

    Returns:
        dict com {codigo, nome, dof} ou None se não encontrado.
    """
    termo = termo.lower()
    for d in listar_disciplinas(session):
        if termo in d["codigo"].lower() or termo in d["nome"].lower():
            return d
    return None


# ── Diário de Classe ──────────────────────────────────────────────────────────

def listar_diarios(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Lista diários de classe do professor no período.

    Args:
        ano_periodo: ex. ``"2026/1"``. None = período selecionado no portal.

    Returns:
        list[dict]: [{dof, nome, codigo, fase, turma, estudantes, pcd, bloqueado}]
          - dof:        identificador da oferta (abre encontros/presenças)
          - bloqueado:  True quando o plano de ensino não está deferido
                        (sem link para o diário)
    """
    data = {"submit": "Consultar"}
    if ano_periodo:
        data["selAnoPeriodo"] = ano_periodo
    resp = _post(session, "diario_classe", data)
    soup = _soup(resp.text)
    result = []
    for tr in soup.find_all("tr"):
        link = tr.find("a", href=re.compile(r"diarioClasseAulas\.jspa\?dof=(\d+)"))
        cells = [re.sub(r"\s+", " ", td.get_text()).strip() for td in tr.find_all("td")]
        if not cells:
            continue
        # Linha típica: componente | obs | fase | turma | estudantes | pcd
        componente = cells[0] if cells else ""
        if not re.search(r"\d{4,5}\s*-", componente):
            continue
        partes = componente.split(" - ", 1)
        codigo = partes[0].strip()
        nome = partes[1].strip() if len(partes) > 1 else componente
        dof = None
        bloqueado = True
        if link:
            m = re.search(r"dof=(\d+)", link.get("href", ""))
            if m:
                dof = m.group(1)
                bloqueado = False
                nome_link = re.sub(r"\s+", " ", link.get_text()).strip()
                if nome_link:
                    partes_l = nome_link.split(" - ", 1)
                    codigo = partes_l[0].strip()
                    nome = partes_l[1].strip() if len(partes_l) > 1 else nome_link
        # Colunas: componente | obs | fase | turma | (vazio/ícone) | estudantes | pcd
        result.append({
            "dof":        dof,
            "codigo":     codigo,
            "nome":       nome,
            "fase":       cells[2] if len(cells) > 2 else "",
            "turma":      cells[3] if len(cells) > 3 else "",
            "estudantes": cells[5] if len(cells) > 5 else (cells[4] if len(cells) > 4 else ""),
            "pcd":        cells[6] if len(cells) > 6 else (cells[5] if len(cells) > 5 else ""),
            "bloqueado":  bloqueado,
        })
    return result


def abrir_diario(session: Session, dof: str) -> str:
    """Retorna HTML bruto do quadro de encontros do diário.

    Args:
        dof: código DOF da disciplina ofertada.
    """
    resp = session.get(
        f"{BASE_URL}{MODULOS['diario_aulas']}",
        params={"dof": dof},
    )
    return resp.text


def listar_encontros(session: Session, dof: str) -> list[dict]:
    """Lista os encontros (aulas) do quadro do diário de classe.

    Args:
        dof: código DOF da disciplina (campo ``dof`` de ``listar_diarios`` /
             ``listar_disciplinas``).

    Returns:
        list[dict]: [{aula, titulo, data, matriculados, presencial, pode_remover}]
          - aula:         ID usado em ``obter_presencas_encontro`` / salvar faltas
          - presencial:   True/False/None
          - pode_remover: se o portal exibe "Remover Encontro"
    """
    resp = session.post(
        f"{BASE_URL}/portal/modules/prof/diarioClasseAulasQuadro.jspa",
        data={"action": "getQuadro", "dof": dof},
    )
    soup = _soup(resp.text)
    encontros = []
    for div in soup.find_all("div", id=re.compile(r"^a_\d+")):
        aula_id = div.get("id", "").replace("a_", "", 1)
        titulo_el = div.find("h3")
        titulo = re.sub(r"\s+", " ", titulo_el.get_text()).strip() if titulo_el else ""
        texto = re.sub(r"\s+", " ", div.get_text(" ")).strip()
        m_data = re.search(r"Data:\s*(.+?)(?:\s+Matriculados:|$)", texto)
        m_mat = re.search(r"Matriculados:\s*(\d+)", texto)
        presencial = None
        if re.search(r"\bNão presencial\b", texto, re.I):
            presencial = False
        elif re.search(r"\bPresencial\b", texto, re.I):
            presencial = True
        encontros.append({
            "aula":         aula_id,
            "titulo":       titulo,
            "data":         m_data.group(1).strip() if m_data else "",
            "matriculados": int(m_mat.group(1)) if m_mat else None,
            "presencial":   presencial,
            "pode_remover": "Remover Encontro" in texto or "delEncontro" in str(div),
        })
    return encontros


def adicionar_encontro(session: Session, dof: str) -> dict:
    """Adiciona um encontro ao quadro do diário (mesma ação do botão do portal).

    Returns:
        dict com {sucesso, status_code, encontros}
    """
    resp = session.post(
        f"{BASE_URL}/portal/modules/prof/diarioClasseAulasQuadro.jspa",
        data={"action": "addEncontro", "dof": dof},
    )
    return {
        "sucesso": resp.status_code == 200,
        "status_code": resp.status_code,
        "encontros": listar_encontros(session, dof) if resp.status_code == 200 else [],
    }


def remover_encontro(session: Session, aula: str, dof: str | None = None) -> dict:
    """Remove um encontro do quadro.

    Falha se houver QR Code de presença em aberto.

    Args:
        aula: ID do encontro.
        dof:  opcional; se informado, devolve a lista atualizada de encontros.
    """
    resp = session.post(
        f"{BASE_URL}/portal/modules/prof/diarioClasseAulasQuadro.jspa",
        data={"action": "delEncontro", "aula": aula},
    )
    out = {
        "sucesso": resp.status_code == 200,
        "status_code": resp.status_code,
    }
    if dof and resp.status_code == 200:
        out["encontros"] = listar_encontros(session, dof)
    return out


def definir_encontro_presencial(session: Session, aula: str, presencial: bool) -> dict:
    """Marca o encontro como presencial (S) ou não presencial (N).

    Em EAD, encontros não presenciais ocultam o quadro de faltas.
    """
    resp = session.post(
        f"{BASE_URL}/portal/modules/prof/diarioClassePresencasTipo.jspa",
        data={
            "action": "setPresencial",
            "aula": aula,
            "presencial": "S" if presencial else "N",
        },
    )
    return {"sucesso": resp.status_code == 200, "status_code": resp.status_code}


def _parse_presencas_html(html: str) -> dict:
    """Extrai metadados e alunos da página Conteúdo/Faltas."""
    soup = _soup(html)
    if "Diário de Classe publicado" in html:
        h2 = soup.find("h2")
        return {
            "publicado": True,
            "disciplina": re.sub(r"\s+", " ", h2.get_text()).strip() if h2 else "",
            "aula": None,
            "alunos": [],
            "mensagem": "Diário de Classe publicado! Contate a Secretaria Acadêmica!",
        }

    form = soup.find("form", id="frmPres") or soup.find("form")
    def _val(name, default=""):
        if not form:
            return default
        el = form.find(["input", "textarea", "select"], attrs={"name": name})
        if not el:
            return default
        if el.name == "textarea":
            return el.get_text()
        if el.name == "select":
            opt = el.find("option", selected=True) or el.find("option")
            return opt.get("value", "") if opt else default
        return el.get("value", default) or default

    aula = _val("aula")
    alunos = []
    for inp in soup.select("input[name^=presencas_]"):
        ra = inp["name"].split("_", 1)[1]
        tr = inp.find_parent("tr")
        tds_txt = []
        if tr:
            for td in tr.find_all("td", recursive=False):
                # tooltip "Dados pessoais" polui o texto — remove antes de ler
                clone = _soup(str(td)).find("td")
                tip = clone.select_one(".tooltiptext") if clone else None
                if tip:
                    tip.decompose()
                tds_txt.append(re.sub(r"\s+", " ", clone.get_text(" ")).strip() if clone else "")
        # Colunas: faltas | código | nome | campus | curso | total | situação | histórico
        onchange = inp.get("onchange", "")
        m_adm = re.search(r"atualizaTotalFaltasAndSituacao\(\s*this\s*,\s*(\d+)\s*\)", onchange)
        total_el = soup.find("input", {"name": f"inputTotalFaltas_{ra}"})
        lanc_el = soup.find("input", {"name": f"inputFaltasLancadasNoEncontro_{ra}"})
        alunos.append({
            "ra":              ra,
            "nome":            tds_txt[2] if len(tds_txt) > 2 else "",
            "campus":          tds_txt[3] if len(tds_txt) > 3 else "",
            "curso":           tds_txt[4] if len(tds_txt) > 4 else "",
            "faltas":          int(inp.get("value") or 0),
            "total_faltas":    int(total_el.get("value") or 0) if total_el else None,
            "faltas_encontro_salvas": int(lanc_el.get("value") or 0) if lanc_el else None,
            "situacao":        tds_txt[6] if len(tds_txt) > 6 else "",
            "cod_adm":         m_adm.group(1) if m_adm else None,
        })

    h2 = soup.find("h2")
    return {
        "publicado":     False,
        "disciplina":    re.sub(r"\s+", " ", h2.get_text()).strip() if h2 else "",
        "aula":          aula,
        "data_inicial":  _val("dataula"),
        "data_final":    _val("dataulafinal"),
        "qtd_aulas":     _val("qtdaulas"),
        "conteudo":      _val("conteudo"),
        "observacoes":   _val("obs"),
        "alunos":        alunos,
        "mensagem":      None,
    }


def obter_presencas_encontro(session: Session, aula: str) -> dict:
    """Lê conteúdo e lançamento de faltas de um encontro.

    Args:
        aula: ID do encontro (campo ``aula`` de ``listar_encontros``).

    Returns:
        dict com disciplina, datas, conteúdo, observações e lista de alunos
        ``[{ra, nome, faltas, total_faltas, situacao, ...}]``.

        Se o diário estiver publicado, ``publicado=True`` e ``alunos=[]``.
    """
    resp = session.get(
        f"{BASE_URL}/portal/modules/prof/diarioClassePresencas.jspa",
        params={"aula": aula},
    )
    data = _parse_presencas_html(resp.text)
    data["status_code"] = resp.status_code
    return data


def salvar_presencas_encontro(
    session: Session,
    aula: str,
    faltas: dict[str, int] | None = None,
    *,
    conteudo: str | None = None,
    observacoes: str | None = None,
    data_inicial: str | None = None,
    data_final: str | None = None,
    qtd_aulas: str | int | None = None,
    dry_run: bool = False,
) -> dict:
    """Salva conteúdo e/ou faltas de um encontro.

    O portal grava o formulário inteiro: valores omitidos são reenviados
    como estão hoje na tela.

    Args:
        aula:          ID do encontro.
        faltas:        ``{RA: n_faltas}`` neste encontro (0 = presente).
                       RAs omitidos mantêm o valor atual.
        conteudo:      texto do conteúdo ministrado (até 4000 chars).
        observacoes:   observações do encontro.
        data_inicial / data_final: ``dd/mm/yyyy``.
        qtd_aulas:     quantidade de aulas do encontro (limite de faltas).
        dry_run:       se True, monta o payload e não envia.

    Returns:
        dict com {sucesso, status_code, publicado, alterados, dry_run, ...}
    """
    atual = obter_presencas_encontro(session, aula)
    if atual.get("publicado"):
        return {
            "sucesso": False,
            "publicado": True,
            "mensagem": atual.get("mensagem"),
            "alterados": [],
        }
    if not atual.get("alunos"):
        return {
            "sucesso": False,
            "publicado": False,
            "mensagem": "Nenhum aluno encontrado na lista de presença.",
            "alterados": [],
        }

    faltas = {str(k): int(v) for k, v in (faltas or {}).items()}
    idx = {a["ra"]: a for a in atual["alunos"]}
    desconhecidos = sorted(set(faltas) - set(idx))
    alterados = []
    for ra, n in faltas.items():
        if ra in idx and idx[ra]["faltas"] != n:
            alterados.append({"ra": ra, "nome": idx[ra]["nome"], "de": idx[ra]["faltas"], "para": n})

    # Recarrega HTML para hidden fields e valores base
    resp_get = session.get(
        f"{BASE_URL}/portal/modules/prof/diarioClassePresencas.jspa",
        params={"aula": aula},
    )
    soup = _soup(resp_get.text)
    form = soup.find("form", id="frmPres") or soup.find("form")
    if not form:
        return {"sucesso": False, "mensagem": "Formulário de presença não encontrado.", "alterados": alterados}

    data: dict[str, str] = {}
    for el in form.find_all(["input", "textarea", "select"]):
        name = el.get("name")
        if not name or el.get("type") == "submit":
            continue
        if el.name == "textarea":
            data[name] = el.get_text()
        elif el.name == "select":
            opt = el.find("option", selected=True)
            data[name] = opt.get("value", "") if opt else ""
        elif el.get("type") == "checkbox":
            if el.has_attr("checked"):
                data[name] = el.get("value", "on")
        else:
            data[name] = el.get("value", "") or ""

    data["aula"] = str(aula)
    data["action"] = "salvarPresencas"
    data["submit"] = "Salvar"

    if conteudo is not None:
        data["conteudo"] = conteudo
    if observacoes is not None:
        data["obs"] = observacoes
    if data_inicial is not None:
        data["dataula"] = data_inicial
    if data_final is not None:
        data["dataulafinal"] = data_final
    if qtd_aulas is not None:
        data["qtdaulas"] = str(qtd_aulas)

    qtd_limite = int(data.get("qtdaulas") or atual.get("qtd_aulas") or 0)
    for ra, n in faltas.items():
        if ra not in idx:
            continue
        if n < 0:
            raise ValueError(f"Faltas negativas para RA {ra}.")
        if qtd_limite and n > qtd_limite:
            raise ValueError(
                f"Faltas ({n}) > qtd_aulas ({qtd_limite}) para RA {ra}."
            )
        data[f"presencas_{ra}"] = str(n)

    if dry_run:
        return {
            "sucesso": True,
            "dry_run": True,
            "publicado": False,
            "alterados": alterados,
            "desconhecidos": desconhecidos,
            "payload_campos": len(data),
        }

    resp = session.post(
        f"{BASE_URL}/portal/modules/prof/diarioClassePresencas.jspa",
        data=data,
    )
    pos = _parse_presencas_html(resp.text)
    return {
        "sucesso": resp.status_code == 200 and not pos.get("publicado"),
        "status_code": resp.status_code,
        "dry_run": False,
        "publicado": bool(pos.get("publicado")),
        "alterados": alterados,
        "desconhecidos": desconhecidos,
        "alunos": pos.get("alunos", []),
        "mensagem": pos.get("mensagem"),
    }


def lancar_faltas(
    session: Session,
    aula: str,
    faltosos: dict[str, int] | list[str] | None = None,
    *,
    presentes: list[str] | None = None,
    zerar_demais: bool = False,
    dry_run: bool = False,
    **kwargs,
) -> dict:
    """Atalho amigável para lançar faltas em um encontro.

    Args:
        aula:         ID do encontro.
        faltosos:     ``{RA: n_faltas}`` ou lista de RAs (1 falta cada).
        presentes:    RAs marcados com 0 falta.
        zerar_demais: se True, quem não estiver em ``faltosos`` recebe 0.
        dry_run:      não envia; só simula.
        **kwargs:     repassados a ``salvar_presencas_encontro``
                      (conteudo, observacoes, datas, ...).

    Examples:
        # Só marca faltosos; demais ficam como estão
        lancar_faltas(s, aula, {"412507": 2, "414049": 1})

        # Todo mundo presente, exceto esses
        lancar_faltas(s, aula, faltosos=["412507"], zerar_demais=True)
    """
    mapa: dict[str, int] = {}
    if isinstance(faltosos, dict):
        mapa.update({str(k): int(v) for k, v in faltosos.items()})
    elif isinstance(faltosos, list):
        mapa.update({str(ra): 1 for ra in faltosos})

    if presentes:
        for ra in presentes:
            mapa[str(ra)] = 0

    if zerar_demais:
        atual = obter_presencas_encontro(session, aula)
        if atual.get("publicado"):
            return {
                "sucesso": False,
                "publicado": True,
                "mensagem": atual.get("mensagem"),
                "alterados": [],
            }
        for a in atual.get("alunos", []):
            mapa.setdefault(a["ra"], 0)

    return salvar_presencas_encontro(
        session, aula, faltas=mapa or None, dry_run=dry_run, **kwargs
    )


# ── Plano de Ensino ───────────────────────────────────────────────────────────

def listar_planos_ensino(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Lista planos de ensino do professor no período.

    Args:
        ano_periodo: ex. ``"2026/2"``. None = período atual do portal.

    Returns:
        list[dict]: [{dof, codigo, nome, fase, turma, situacao, observacao}]
    """
    data = {"submit": "Consultar"}
    if ano_periodo:
        data["selAnoPeriodo"] = ano_periodo
    resp = _post(session, "plano_ensino", data)
    soup = _soup(resp.text)
    result = []
    for tr in soup.find_all("tr"):
        link = tr.find("a", href=re.compile(r"editPlanoEnsino\.jspa\?dof=(\d+)"))
        if not link:
            continue
        m = re.search(r"dof=(\d+)", link.get("href", ""))
        if not m:
            continue
        cells = [re.sub(r"\s+", " ", td.get_text()).strip() for td in tr.find_all("td")]
        componente = cells[0] if cells else ""
        partes = componente.split(" - ", 1)
        result.append({
            "dof":         m.group(1),
            "codigo":      partes[0].strip(),
            "nome":        partes[1].strip() if len(partes) > 1 else componente,
            "fase":        cells[1] if len(cells) > 1 else "",
            "turma":       cells[2] if len(cells) > 2 else "",
            "situacao":    cells[7] if len(cells) > 7 else "",
            "observacao":  cells[8] if len(cells) > 8 else "",
        })
    return result


def _campo_plano(soup, name: str) -> str:
    el = soup.find(attrs={"name": name}) or soup.find(id=name)
    if not el:
        return ""
    if el.name == "textarea":
        return el.get_text()
    return el.get("value", "") or ""


def _parse_data_cronograma(dia: str) -> dict:
    """Extrai datas/horários de strings do cronograma do plano."""
    dia = (dia or "").strip()
    out = {
        "dia_raw": dia,
        "data_inicio": None,
        "data_fim": None,
        "hora_inicio": None,
        "hora_fim": None,
        "autoestudo": False,
    }
    if not dia or dia == "-":
        return out
    if re.search(r"autoestudo", dia, re.I):
        out["autoestudo"] = True
        return out
    # 05/10/2026 - 13/12/2026  |  14/10/2026 19:00 - 21:00  |  28/07/2026 19:00 - 20:30
    m_range = re.match(
        r"^(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})$", dia
    )
    if m_range:
        out["data_inicio"], out["data_fim"] = m_range.group(1), m_range.group(2)
        return out
    m_hora = re.match(
        r"^(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})$", dia
    )
    if m_hora:
        out["data_inicio"] = m_hora.group(1)
        out["data_fim"] = m_hora.group(1)
        out["hora_inicio"] = m_hora.group(2)
        out["hora_fim"] = m_hora.group(3)
        return out
    m_data = re.match(r"^(\d{2}/\d{2}/\d{4})", dia)
    if m_data:
        out["data_inicio"] = m_data.group(1)
        out["data_fim"] = m_data.group(1)
    return out


def listar_cronograma_plano(session: Session, dof: str) -> list[dict]:
    """Lista o cronograma (encontros) do plano de ensino.

    Fonte: ``editPlanoEnsinoCronograma.jspa?action=getCronograma`` (somente leitura).

    Returns:
        list[dict]: [{ordem, dia, dia_semana, tipo, conteudo, atividade,
                      data_inicio, data_fim, hora_inicio, hora_fim, autoestudo}]
    """
    resp = session.post(
        f"{BASE_URL}/portal/modules/prof/editPlanoEnsinoCronograma.jspa",
        data={"action": "getCronograma", "dof": dof},
    )
    soup = _soup(resp.text)
    itens = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 6:
            continue
        ordem_txt = re.sub(r"\s+", " ", tds[0].get_text()).strip()
        m_ord = re.search(r"\d+", ordem_txt)
        if not m_ord:
            continue
        # conteúdo pode ter <br/>
        conteudo = tds[4].get_text("\n", strip=True)
        atividade = tds[5].get_text("\n", strip=True)
        dia = re.sub(r"\s+", " ", tds[1].get_text()).strip()
        item = {
            "ordem":      int(m_ord.group(0)),
            "dia":        dia,
            "dia_semana": re.sub(r"\s+", " ", tds[2].get_text()).strip(),
            "tipo":       re.sub(r"\s+", " ", tds[3].get_text()).strip(),
            "conteudo":   conteudo,
            "atividade":  atividade,
        }
        item.update(_parse_data_cronograma(dia))
        itens.append(item)
    return itens


def listar_unidades_plano(session: Session, dof: str) -> list[dict]:
    """Lista unidades de ensino do plano.

    Returns:
        list[dict]: [{ordem, nome, descricao}]
    """
    resp = session.post(
        f"{BASE_URL}/portal/modules/prof/planoEnsinoUnidadeEnsinoList.jspa",
        data={"action": "getUnidadesDeEnsino", "dof": dof},
    )
    soup = _soup(resp.text)
    itens = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        ordem = re.sub(r"\s+", " ", tds[0].get_text()).strip()
        if not ordem.isdigit():
            continue
        itens.append({
            "ordem":     int(ordem),
            "nome":      re.sub(r"\s+", " ", tds[1].get_text()).strip(),
            "descricao": tds[2].get_text("\n", strip=True),
        })
    return itens


def listar_bibliografias_plano(session: Session, dof: str) -> list[dict]:
    """Lista bibliografias (básica/complementar) do plano.

    Returns:
        list[dict]: [{referencia, tipo}]
          - tipo: ``"Básica"`` ou ``"Complementar"``
    """
    resp = session.post(
        f"{BASE_URL}/portal/modules/prof/editPlanoEnsinoBibliografia.jspa",
        data={"action": "getBibliografias", "dof": dof},
    )
    soup = _soup(resp.text)
    itens = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        referencia = re.sub(r"\s+", " ", tds[0].get_text()).strip()
        tipo = re.sub(r"\s+", " ", tds[1].get_text()).strip()
        if not referencia or referencia.lower().startswith("referência"):
            continue
        if tipo.lower() not in ("básica", "basica", "complementar"):
            # evita linhas de metadados
            if "básic" not in tipo.lower() and "complement" not in tipo.lower():
                continue
        itens.append({"referencia": referencia, "tipo": tipo})
    return itens


def listar_avaliacoes_plano(session: Session, dof: str) -> list[dict]:
    """Lista avaliações cadastradas no plano de ensino (A1/A2 etc.).

    Returns:
        list[dict]: [{tipo, nome, peso, descritivo, data_inicial, data_final}]
    """
    resp = session.post(
        f"{BASE_URL}/portal/modules/prof/editPlanoEnsinoAvaliacao.jspa",
        data={"action": "getAvaliacoes", "dof": dof},
    )
    soup = _soup(resp.text)
    itens = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        tipo = re.sub(r"\s+", " ", tds[0].get_text()).strip()
        if not tipo or tipo.lower().startswith("tipo"):
            continue
        itens.append({
            "tipo":          tipo,
            "nome":          re.sub(r"\s+", " ", tds[1].get_text()).strip(),
            "peso":          re.sub(r"\s+", " ", tds[2].get_text()).strip(),
            "descritivo":    tds[3].get_text("\n", strip=True),
            "data_inicial":  re.sub(r"\s+", " ", tds[4].get_text()).strip() if len(tds) > 4 else "",
            "data_final":    re.sub(r"\s+", " ", tds[5].get_text()).strip() if len(tds) > 5 else "",
        })
    return itens


def obter_plano_ensino(session: Session, dof: str) -> dict:
    """Lê o plano de ensino completo de uma oferta (somente leitura).

    Inclui textos principais, unidades, cronograma, bibliografias e avaliações.

    Args:
        dof: código DOF da disciplina ofertada.

    Returns:
        dict com chaves:
          dof, disciplina, objetivo_geral, justificativa, metodologia,
          avaliacao, unidades_texto, unidades, cronograma, bibliografias,
          avaliacoes
    """
    resp = session.get(
        f"{BASE_URL}/portal/modules/prof/editPlanoEnsino.jspa",
        params={"dof": dof},
    )
    soup = _soup(resp.text)
    h2 = soup.find("h2")
    disciplina = re.sub(r"\s+", " ", h2.get_text()).strip() if h2 else ""
    # fallback: metadados na página
    if not disciplina:
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) >= 2 and "componente" in tds[0].get_text().lower():
                disciplina = re.sub(r"\s+", " ", tds[1].get_text()).strip()
                break

    return {
        "dof":             str(dof),
        "disciplina":      disciplina,
        "objetivo_geral":  _campo_plano(soup, "objetivoGeral"),
        "justificativa":   _campo_plano(soup, "justificativa"),
        "metodologia":     _campo_plano(soup, "metodologiaPEA"),
        "avaliacao":       _campo_plano(soup, "avaliacaoPEA"),
        "unidades_texto":  _campo_plano(soup, "unidadesEnsinoPEA"),
        "unidades":        listar_unidades_plano(session, dof),
        "cronograma":      listar_cronograma_plano(session, dof),
        "bibliografias":   listar_bibliografias_plano(session, dof),
        "avaliacoes":      listar_avaliacoes_plano(session, dof),
    }


def analisar_plano_trilha(session: Session, dof: str, *, incluir_atividades: bool = False) -> dict:
    """Compara (somente leitura) o plano de ensino com a trilha atual no Moodle.

    Não cria nem altera seções/atividades. Usa o plano como fonte e a estrutura
    do curso Moodle como espelho atual.

    Args:
        dof: código DOF.
        incluir_atividades: se True, lista atividades de cada seção Moodle
            (mais lento).

    Returns:
        dict com ``plano``, ``trilha`` (estrutura Moodle) e ``resumo``
        (contagens e padrões detectados).
    """
    from . import moodle as moodle_mod

    plano = obter_plano_ensino(session, dof)
    ms, course_id = moodle_mod.abrir_curso(session, dof)
    trilha = moodle_mod.obter_estrutura_curso(
        ms, course_id, incluir_atividades=incluir_atividades
    )

    datas_plano = sorted({
        c["data_inicio"] for c in plano["cronograma"]
        if c.get("data_inicio")
    })
    datas_trilha = sorted({
        s.get("data") for s in trilha["secoes"] if s.get("data")
    })

    return {
        "dof": dof,
        "plano": plano,
        "trilha": trilha,
        "resumo": {
            "n_unidades_plano": len(plano["unidades"]),
            "n_cronograma_plano": len(plano["cronograma"]),
            "n_bibliografias": len(plano["bibliografias"]),
            "n_avaliacoes_plano": len(plano["avaliacoes"]),
            "n_secoes_moodle": trilha["n_secoes"],
            "padrao_trilha": trilha["padrao"],
            "datas_plano": datas_plano,
            "datas_trilha": datas_trilha,
            "datas_so_no_plano": sorted(set(datas_plano) - set(datas_trilha)),
            "datas_so_na_trilha": sorted(set(datas_trilha) - set(datas_plano)),
        },
    }


def _detectar_padrao_plano(
    plano: dict,
    *,
    padrao: str | None = None,
    trilha: dict | None = None,
) -> str:
    """Resolve o template da trilha: ead_semanas | presencial_aulas."""
    if padrao in ("ead_semanas", "presencial_aulas"):
        return padrao
    if trilha and trilha.get("padrao") in ("ead_semanas", "presencial_aulas"):
        return trilha["padrao"]
    disc = (plano.get("disciplina") or "").upper()
    if "EAD" in disc:
        return "ead_semanas"
    # Heurística: muitos encontros datados → presencial
    datados = [
        c for c in plano.get("cronograma", [])
        if c.get("data_inicio") and not c.get("autoestudo")
        and c.get("data_inicio") == c.get("data_fim")
    ]
    if len(datados) >= 3:
        return "presencial_aulas"
    return "ead_semanas"


def _inferir_semanas_por_unidade(trilha: dict | None, n_unidades: int) -> tuple[list[int], list[list[str]]] | tuple[None, None]:
    """Infere semanas por unidade e nomes das seções já existentes.

    Returns:
        (contagens, nomes_por_unidade) ou (None, None).
    """
    if not trilha or n_unidades <= 0:
        return None, None
    secoes = trilha.get("secoes") or []
    grupos: list[list[str]] = []
    atual: list[str] = []
    contando = False
    for s in secoes:
        papel = s.get("papel")
        if papel == "unidade":
            if contando:
                grupos.append(atual)
            contando = True
            atual = []
        elif papel == "semana" and contando:
            atual.append(s.get("nome") or "")
        elif papel in ("avaliacao", "apoio", "forum") and contando:
            grupos.append(atual)
            contando = False
            atual = []
    if contando:
        grupos.append(atual)
    if len(grupos) == n_unidades and all(len(g) > 0 for g in grupos):
        return [len(g) for g in grupos], grupos
    n_sem = sum(1 for s in secoes if s.get("papel") == "semana")
    if n_sem > 0 and n_unidades > 0:
        base, resto = divmod(n_sem, n_unidades)
        if base > 0:
            contagens = [base + (1 if i < resto else 0) for i in range(n_unidades)]
            return contagens, None
    return None, None


def _formato_aula_existente(trilha: dict | None) -> str:
    """Retorna 'numerada' se o curso usa 'Aula N - data', senão 'simples'."""
    if not trilha:
        return "simples"
    for s in trilha.get("secoes") or []:
        if re.search(r"(?i)^aula\s+\d+\s*-", s.get("nome") or ""):
            return "numerada"
    return "simples"


def _heuristica_tipo_atividade(texto: str) -> str | None:
    """Sugere tipo Moodle a partir do texto do plano. None = sem sugestão clara."""
    t = (texto or "").lower()
    if not t.strip():
        return None
    if re.search(r"\b(prova|question[aá]rio|quiz|objetiva)\b", t):
        return "quiz"
    if re.search(r"\b(f[oó]rum|discuss[aã]o)\b", t):
        return "hsuforum"
    if re.search(r"\b(webconfer[eê]ncia|webconf|url|link|http)\b", t):
        return "url"
    if re.search(r"\b(pasta|materiais?|material de apoio)\b", t):
        return "folder"
    if re.search(r"\b(tarefa|atividade avaliativa|trabalho|mvp|entrega)\b", t):
        return "assign"
    return None


def planejar_secoes_do_plano(
    plano: dict,
    *,
    padrao: str | None = None,
    semanas_por_unidade: list[int] | None = None,
    trilha: dict | None = None,
) -> list[dict]:
    """Monta a lista desejada de seções Moodle a partir do plano (sem HTTP).

    Args:
        plano: retorno de ``obter_plano_ensino``.
        padrao: ``ead_semanas`` | ``presencial_aulas`` | None (auto).
        semanas_por_unidade: obrigatório no EAD se a trilha atual não permitir
            inferir (ex. ``[2, 3]`` = 2 semanas na U1 e 3 na U2).
        trilha: estrutura atual (``obter_estrutura_curso``) para inferir formato.

    Returns:
        list[dict]: [{nome, papel, data, unidade_ordem, semana_rotulo,
                      fonte, conteudo, atividade, ordem_cronograma}]
    """
    padrao = _detectar_padrao_plano(plano, padrao=padrao, trilha=trilha)
    secoes: list[dict] = []

    def add(nome, papel, **extra):
        item = {
            "nome": nome,
            "papel": papel,
            "data": extra.get("data"),
            "unidade_ordem": extra.get("unidade_ordem"),
            "semana_rotulo": extra.get("semana_rotulo"),
            "fonte": extra.get("fonte", "template"),
            "conteudo": extra.get("conteudo"),
            "atividade": extra.get("atividade"),
            "ordem_cronograma": extra.get("ordem_cronograma"),
        }
        secoes.append(item)

    add("Apresentação", "apresentacao")

    if padrao == "presencial_aulas":
        add("Plano de Ensino", "plano")
        add("Material Didático", "material")
        fmt = _formato_aula_existente(trilha)
        aula_n = 0
        for c in plano.get("cronograma") or []:
            if c.get("autoestudo"):
                continue
            data = c.get("data_inicio")
            # só encontros de um dia (não intervalos longos de autoestudo)
            if not data or c.get("data_inicio") != c.get("data_fim"):
                # intervalo multiperíodo → seção não presencial opcional
                if data and c.get("data_fim") and c.get("data_inicio") != c.get("data_fim"):
                    tipo = (c.get("tipo") or "").lower()
                    if "não presencial" in tipo or "nao presencial" in tipo:
                        continue  # conteúdo embutido nas aulas; não gera seção
                continue
            aula_n += 1
            if fmt == "numerada":
                nome = f"Aula {aula_n} - {data}"
            else:
                nome = f"Aula - {data}"
            add(
                nome, "aula",
                data=data,
                fonte="cronograma",
                conteudo=c.get("conteudo"),
                atividade=c.get("atividade"),
                ordem_cronograma=c.get("ordem"),
            )
        # Avaliações
        tem_a2 = any(
            (a.get("tipo") or "").upper() == "A2" or "exame" in (a.get("nome") or "").lower()
            for a in (plano.get("avaliacoes") or [])
        )
        if tem_a2 or any("exame" in (c.get("conteudo") or "").lower() for c in plano.get("cronograma") or []):
            add("Exame Final | A2", "avaliacao", fonte="avaliacoes")
        else:
            add("Avaliações", "avaliacao", fonte="avaliacoes")

    else:  # ead_semanas
        unidades = plano.get("unidades") or []
        n_u = len(unidades)
        nomes_inferidos = None
        semanas = semanas_por_unidade
        if semanas is None:
            semanas, nomes_inferidos = _inferir_semanas_por_unidade(trilha, n_u)
        if n_u == 0:
            raise ValueError(
                "Plano EAD sem unidades cadastradas; não é possível montar a trilha."
            )
        if not semanas or len(semanas) != n_u:
            raise ValueError(
                "Para EAD informe semanas_por_unidade (ex. [2, 3]) ou use um curso "
                "Moodle que já tenha seções Semana sob cada Unidade para inferir."
            )
        # Preferir nomes de unidade já existentes na trilha
        unidades_exist = [
            s.get("nome") for s in (trilha or {}).get("secoes") or []
            if s.get("papel") == "unidade"
        ]
        crono = [
            c for c in (plano.get("cronograma") or [])
            if not c.get("autoestudo")
        ]
        encontros = [
            c for c in crono
            if "presencial" in (c.get("tipo") or "").lower()
            and c.get("data_inicio") == c.get("data_fim")
        ]
        semana_global = 1
        for i, u in enumerate(unidades):
            ordem_u = u.get("ordem", i + 1)
            nome_u = (u.get("nome") or f"Unidade {ordem_u}").strip()
            if i < len(unidades_exist) and unidades_exist[i]:
                nome_secao_u = unidades_exist[i]
            else:
                nome_secao_u = f"UNIDADE {ordem_u} | {nome_u.upper()}"
            add(
                nome_secao_u,
                "unidade",
                unidade_ordem=ordem_u,
                fonte="unidades",
                conteudo=u.get("descricao"),
            )
            n_sem = semanas[i]
            labels = None
            if nomes_inferidos and i < len(nomes_inferidos):
                labels = nomes_inferidos[i]
            for j in range(n_sem):
                if labels and j < len(labels) and labels[j]:
                    rotulo = labels[j]
                else:
                    rotulo = f"Semana {semana_global}"
                c_ref = encontros[min(i, len(encontros) - 1)] if encontros else (crono[0] if crono else None)
                add(
                    rotulo, "semana",
                    unidade_ordem=ordem_u,
                    semana_rotulo=rotulo,
                    fonte="semanas_por_unidade",
                    conteudo=(c_ref or {}).get("conteudo"),
                    atividade=(c_ref or {}).get("atividade"),
                    ordem_cronograma=(c_ref or {}).get("ordem"),
                    data=(c_ref or {}).get("data_inicio") if j == 0 and c_ref and c_ref.get("data_inicio") == c_ref.get("data_fim") else None,
                )
                semana_global += 1

        add("Exame Final | A2", "avaliacao", fonte="avaliacoes")
        add("APOIO PEDAGÓGICO", "apoio", fonte="template")
        add("Tira-dúvidas", "forum", fonte="template")
        add("Tutoriais", "apoio", fonte="template")

    return secoes


def planejar_atividades_do_plano(
    plano: dict,
    secoes_planejadas: list[dict],
    *,
    padrao: str | None = None,
) -> list[dict]:
    """Sugere atividades Moodle a partir do plano e das seções planejadas.

    Não inclui LTI. Tipos: assign, quiz, hsuforum, folder, url.

    Returns:
        list[dict]: [{secao_nome, tipo, nome, intro, fonte, ordem_cronograma}]
    """
    padrao = padrao or _detectar_padrao_plano(plano)
    atividades: list[dict] = []

    # Fórum de apresentação
    for s in secoes_planejadas:
        if s["papel"] == "apresentacao":
            atividades.append({
                "secao_nome": s["nome"],
                "tipo": "hsuforum",
                "nome": "Fórum de apresentação",
                "intro": "Apresente-se à turma.",
                "fonte": "template",
                "ordem_cronograma": None,
            })
            break

    # Material didático: pasta
    for s in secoes_planejadas:
        if s["papel"] == "material":
            atividades.append({
                "secao_nome": s["nome"],
                "tipo": "folder",
                "nome": "Material Didático",
                "intro": "Arquivos de apoio da disciplina.",
                "fonte": "template",
                "ordem_cronograma": None,
            })
            break

    # Por seção de aula/semana: heurística no texto
    for s in secoes_planejadas:
        if s["papel"] not in ("aula", "semana"):
            continue
        texto = " ".join(filter(None, [s.get("atividade"), s.get("conteudo")]))
        tipo = _heuristica_tipo_atividade(texto)
        if not tipo:
            # padrão suave: pasta de material da aula
            tipo = "folder"
            nome = f"Material — {s['nome']}"
        else:
            if tipo == "quiz":
                nome = f"Questionário — {s['nome']}"
            elif tipo == "assign":
                nome = f"Atividade — {s['nome']}"
            elif tipo == "hsuforum":
                nome = f"Fórum — {s['nome']}"
            elif tipo == "url":
                nome = f"Webconferência — {s['nome']}"
            else:
                nome = f"Material — {s['nome']}"
        atividades.append({
            "secao_nome": s["nome"],
            "tipo": tipo,
            "nome": nome[:200],
            "intro": (s.get("conteudo") or "")[:2000],
            "fonte": "cronograma" if s.get("ordem_cronograma") else "heuristica",
            "ordem_cronograma": s.get("ordem_cronograma"),
        })

    # Avaliações do plano → assign/quiz
    for a in plano.get("avaliacoes") or []:
        secao_aval = next((s for s in secoes_planejadas if s["papel"] == "avaliacao"), None)
        if not secao_aval:
            continue
        desc = (a.get("descritivo") or "") + " " + (a.get("nome") or "")
        tipo = _heuristica_tipo_atividade(desc) or "assign"
        if tipo == "url":
            tipo = "assign"
        atividades.append({
            "secao_nome": secao_aval["nome"],
            "tipo": tipo,
            "nome": a.get("nome") or a.get("tipo") or "Avaliação",
            "intro": a.get("descritivo") or "",
            "fonte": "avaliacoes",
            "ordem_cronograma": None,
        })

    # Fórum tira-dúvidas
    for s in secoes_planejadas:
        if s["papel"] == "forum" or "tira" in s["nome"].lower():
            atividades.append({
                "secao_nome": s["nome"],
                "tipo": "hsuforum",
                "nome": "Tira-dúvidas",
                "intro": "Canal para dúvidas da disciplina.",
                "fonte": "template",
                "ordem_cronograma": None,
            })
            break

    return atividades


def _match_secao_planejada(desejada: dict, existentes: list[dict]) -> dict | None:
    """Encontra seção Moodle correspondente à planejada."""
    nome_d = (desejada.get("nome") or "").strip().lower()
    data_d = desejada.get("data")
    for s in existentes:
        if data_d and s.get("data") == data_d and desejada.get("papel") == "aula":
            return s
        nome_e = (s.get("nome") or "").strip().lower()
        if nome_e == nome_d:
            return s
        # match parcial para unidade/semana
        if desejada.get("papel") in ("unidade", "semana", "avaliacao", "apresentacao", "plano", "material", "apoio", "forum"):
            if nome_d and (nome_d in nome_e or nome_e in nome_d):
                return s
    return None


def planejar_sincronizacao_trilha(
    session: Session,
    dof: str,
    *,
    incluir_atividades: bool = False,
    padrao: str | None = None,
    semanas_por_unidade: list[int] | None = None,
) -> dict:
    """Calcula o diff plano × Moodle sem alterar nada.

    Returns:
        dict com padrao, secoes_planejadas, secoes_criar, secoes_atualizar,
        secoes_ignorar, atividades_planejadas, atividades_criar, atividades_ignorar,
        plano, trilha.
    """
    from . import moodle as moodle_mod

    plano = obter_plano_ensino(session, dof)
    ms, course_id = moodle_mod.abrir_curso(session, dof)
    trilha = moodle_mod.obter_estrutura_curso(
        ms, course_id, incluir_atividades=incluir_atividades
    )

    padrao_res = _detectar_padrao_plano(plano, padrao=padrao, trilha=trilha)
    secoes_planejadas = planejar_secoes_do_plano(
        plano,
        padrao=padrao_res,
        semanas_por_unidade=semanas_por_unidade,
        trilha=trilha,
    )

    existentes = trilha.get("secoes") or []
    criar, atualizar, ignorar = [], [], []
    for desejada in secoes_planejadas:
        match = _match_secao_planejada(desejada, existentes)
        if not match:
            criar.append({**desejada, "acao": "criar"})
        elif (match.get("nome") or "").strip() != (desejada.get("nome") or "").strip():
            atualizar.append({
                **desejada,
                "acao": "atualizar",
                "section_id": match.get("section_id"),
                "nome_atual": match.get("nome"),
            })
            ignorar.append({  # já existe; rename é opcional no sync
                **desejada,
                "acao": "existe",
                "section_id": match.get("section_id"),
                "nome_atual": match.get("nome"),
            })
        else:
            ignorar.append({
                **desejada,
                "acao": "ignorar",
                "section_id": match.get("section_id"),
                "nome_atual": match.get("nome"),
            })

    atividades_planejadas = planejar_atividades_do_plano(
        plano, secoes_planejadas, padrao=padrao_res
    ) if incluir_atividades else []

    # index atividades existentes por seção
    ativ_por_secao: dict[str, list] = {}
    for s in existentes:
        ativ_por_secao[s.get("nome", "")] = s.get("atividades") or []

    ativ_criar, ativ_ignorar = [], []
    for a in atividades_planejadas:
        # resolve seção destino (nome planejado ou match)
        secao_match = _match_secao_planejada(
            {"nome": a["secao_nome"], "papel": "outro", "data": None},
            existentes,
        )
        existentes_ativ = []
        if secao_match:
            existentes_ativ = secao_match.get("atividades") or ativ_por_secao.get(secao_match.get("nome", ""), [])
        nome_l = (a.get("nome") or "").lower()
        found = None
        for ea in existentes_ativ:
            if nome_l and nome_l in (ea.get("nome") or "").lower():
                found = ea
                break
            if a.get("tipo") and ea.get("tipo") == a["tipo"] and nome_l[:20] in (ea.get("nome") or "").lower():
                found = ea
                break
        if found:
            ativ_ignorar.append({**a, "acao": "ignorar", "activity_id": found.get("activity_id")})
        else:
            ativ_criar.append({
                **a,
                "acao": "criar",
                "section_id": secao_match.get("section_id") if secao_match else None,
                "section_num": None,  # preenchido no sync
            })

    return {
        "dof": str(dof),
        "course_id": course_id,
        "padrao": padrao_res,
        "plano": plano,
        "trilha": trilha,
        "secoes_planejadas": secoes_planejadas,
        "secoes_criar": criar,
        "secoes_atualizar": atualizar,
        "secoes_ignorar": [x for x in ignorar if x.get("acao") == "ignorar"],
        "atividades_planejadas": atividades_planejadas,
        "atividades_criar": ativ_criar,
        "atividades_ignorar": ativ_ignorar,
    }


def sincronizar_trilha_do_plano(
    session: Session,
    dof: str,
    *,
    criar_secoes: bool = True,
    criar_atividades: bool = False,
    atualizar_nomes: bool = False,
    padrao: str | None = None,
    semanas_por_unidade: list[int] | None = None,
    dry_run: bool = True,
) -> dict:
    """Sincroniza a trilha Moodle com o plano (nunca apaga conteúdo).

    Por padrão só simula (``dry_run=True``). Atividades só são criadas se
    ``criar_atividades=True``.
    """
    from . import moodle as moodle_mod

    plano_sync = planejar_sincronizacao_trilha(
        session,
        dof,
        incluir_atividades=criar_atividades,
        padrao=padrao,
        semanas_por_unidade=semanas_por_unidade,
    )
    course_id = plano_sync["course_id"]
    detalhes: list[dict] = []
    criados_s, atualizados_s, criados_a = [], [], []

    if dry_run:
        if criar_secoes:
            for s in plano_sync["secoes_criar"]:
                detalhes.append({"tipo": "secao", "acao": "criar", "dry_run": True, **s})
                criados_s.append(s)
            if atualizar_nomes:
                for s in plano_sync["secoes_atualizar"]:
                    detalhes.append({"tipo": "secao", "acao": "atualizar", "dry_run": True, **s})
                    atualizados_s.append(s)
        if criar_atividades:
            for a in plano_sync["atividades_criar"]:
                detalhes.append({"tipo": "atividade", "acao": "criar", "dry_run": True, **a})
                criados_a.append(a)
        return {
            "sucesso": True,
            "dry_run": True,
            "padrao": plano_sync["padrao"],
            "course_id": course_id,
            "criados": criados_s,
            "atualizados": atualizados_s,
            "atividades_criadas": criados_a,
            "ignorados": {
                "secoes": plano_sync["secoes_ignorar"],
                "atividades": plano_sync["atividades_ignorar"],
            },
            "detalhes": detalhes,
            "erros": [],
        }

    # Escrita real
    erros: list[str] = []
    ms, _ = moodle_mod.abrir_curso(session, dof)

    if criar_secoes:
        for s in plano_sync["secoes_criar"]:
            try:
                r = moodle_mod.criar_secao(ms, course_id, s["nome"], dry_run=False)
                detalhes.append({"tipo": "secao", **r, "planejado": s})
                if r.get("sucesso"):
                    criados_s.append(r)
                else:
                    erros.append(r.get("mensagem") or f"Falha ao criar seção {s['nome']}")
            except Exception as exc:  # noqa: BLE001
                erros.append(f"criar_secao({s['nome']}): {exc}")
        if atualizar_nomes:
            for s in plano_sync["secoes_atualizar"]:
                try:
                    r = moodle_mod.atualizar_secao(
                        ms, s["section_id"], nome=s["nome"], dry_run=False
                    )
                    detalhes.append({"tipo": "secao", **r, "planejado": s})
                    if r.get("sucesso"):
                        atualizados_s.append(r)
                    else:
                        erros.append(r.get("mensagem") or f"Falha ao atualizar {s['nome']}")
                except Exception as exc:  # noqa: BLE001
                    erros.append(f"atualizar_secao({s.get('section_id')}): {exc}")

    if criar_atividades:
        # Relê estrutura para mapear section_num
        trilha = moodle_mod.obter_estrutura_curso(ms, course_id, incluir_atividades=True)
        nome_para_num = {
            s["nome"]: idx for idx, s in enumerate(trilha["secoes"])
        }
        # também por match parcial
        for a in plano_sync["atividades_criar"]:
            section_num = None
            sid = a.get("section_id")
            for idx, s in enumerate(trilha["secoes"]):
                if sid and s.get("section_id") == sid:
                    section_num = idx
                    break
                if (a["secao_nome"] or "").lower() in (s.get("nome") or "").lower():
                    section_num = idx
                    break
            if section_num is None:
                section_num = nome_para_num.get(a["secao_nome"])
            if section_num is None:
                erros.append(f"Seção destino não encontrada para atividade {a['nome']}")
                continue
            try:
                r = moodle_mod.criar_atividade(
                    ms,
                    course_id,
                    section_num,
                    a["tipo"],
                    a["nome"],
                    intro=a.get("intro"),
                    dry_run=False,
                )
                detalhes.append({"tipo": "atividade", **r, "planejado": a})
                if r.get("sucesso"):
                    criados_a.append(r)
                else:
                    erros.append(r.get("mensagem") or f"Falha ao criar {a['nome']}")
            except Exception as exc:  # noqa: BLE001
                erros.append(f"criar_atividade({a['nome']}): {exc}")

    return {
        "sucesso": len(erros) == 0,
        "dry_run": False,
        "padrao": plano_sync["padrao"],
        "course_id": course_id,
        "criados": criados_s,
        "atualizados": atualizados_s,
        "atividades_criadas": criados_a,
        "ignorados": {
            "secoes": plano_sync["secoes_ignorar"],
            "atividades": plano_sync["atividades_ignorar"],
        },
        "detalhes": detalhes,
        "erros": erros,
    }


# ── Avaliações e Notas ────────────────────────────────────────────────────────

def consultar_notas(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Retorna tabela de notas consolidada por disciplina.

    Returns:
        list[dict] com aluno, notas e situação.
    """
    params = {"selAnoPeriodo": ano_periodo} if ano_periodo else None
    resp = _get(session, "consulta_notas", params)
    return _tabela(_soup(resp.text))


def lista_presenca(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Retorna lista de presença A1 (estudantes aptos).

    Returns:
        list[dict] com nome, RA e dados do estudante.
    """
    params = {"selAnoPeriodo": ano_periodo} if ano_periodo else None
    resp = _get(session, "lista_presenca_a1", params)
    return _tabela(_soup(resp.text))


def lista_estudantes_a2(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Retorna lista de estudantes em recuperação (A2).

    Returns:
        list[dict] com nome, RA e nota A1.
    """
    params = {"selAnoPeriodo": ano_periodo} if ano_periodo else None
    resp = _get(session, "lista_estudantes_a2", params)
    return _tabela(_soup(resp.text))


# ── Mensagens ─────────────────────────────────────────────────────────────────

def _as_list(valor: str | list[str] | None) -> list[str]:
    if valor is None:
        return []
    if isinstance(valor, list):
        return [str(v) for v in valor]
    return [str(valor)]


def _resolver_dofs(session: Session, disciplinas: str | list[str] | None) -> list[str]:
    """Aceita DOF numérico (7+ dígitos), código ou nome da disciplina."""
    itens = _as_list(disciplinas)
    if not itens:
        raise ValueError("Informe ao menos uma disciplina (DOF ou nome/código).")

    # DOFs conhecidos das telas de mensagem / aula online
    dofs_validos: set[str] = set()
    try:
        dofs_validos.update(t["dof"] for t in listar_turmas_mensagem(session) if t.get("dof"))
    except Exception:
        pass
    try:
        dofs_validos.update(d["dof"] for d in listar_disciplinas(session) if d.get("dof"))
    except Exception:
        pass

    dofs: list[str] = []
    for item in itens:
        if item.isdigit() and (item in dofs_validos or len(item) >= 7):
            dofs.append(item)
            continue
        disc = buscar_disciplina(session, item)
        if not disc:
            raise ValueError(f"Disciplina '{item}' não encontrada.")
        dofs.append(disc["dof"])

    vistos: set[str] = set()
    out: list[str] = []
    for d in dofs:
        if d not in vistos:
            vistos.add(d)
            out.append(d)
    return out


def listar_turmas_mensagem(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Lista turmas disponíveis para mensagem direta / push.

    Returns:
        list[dict] com dof, componente, fase, turma, estudantes.
    """
    params = {"selAnoPeriodo": ano_periodo} if ano_periodo else None
    resp = _get(session, "mensagem_alunos", params)
    soup = _soup(resp.text)
    rows = _tabela(soup)
    dofs_por_ordem = [
        cb.get("value")
        for cb in soup.select("input[name='discturma[]']")
        if cb.get("value")
    ]
    result = []
    for i, row in enumerate(rows):
        dof = dofs_por_ordem[i] if i < len(dofs_por_ordem) else ""
        result.append({
            "dof":        dof,
            "componente": row.get("Componente curricular", ""),
            "fase":       row.get("Fase", ""),
            "turma":      row.get("Turma", ""),
            "estudantes": row.get("Estudantes", ""),
            "pcd":        row.get("Pessoas com Deficiência (PcD)", ""),
        })
    return result


def listar_alunos_para_mensagem(
    session: Session,
    disciplinas: str | list[str],
    ano_periodo: str | None = None,
) -> list[dict]:
    """Lista alunos (RA, nome, e-mail) das turmas selecionadas.

    Args:
        disciplinas: DOF, nome/código da disciplina, ou lista.
        ano_periodo: opcional (ex. '2026/1') — aplicado na tela inicial.

    Returns:
        list[dict]: [{ra, nome, email, dof}, ...]
    """
    if ano_periodo:
        _get(session, "mensagem_alunos", {"selAnoPeriodo": ano_periodo})

    dofs = _resolver_dofs(session, disciplinas)
    resp = session.post(
        f"{BASE_URL}{MODULOS['mensagem_selecionar']}",
        data={"origem": "D", "discturma[]": dofs},
        allow_redirects=True,
    )
    soup = _soup(resp.text)
    alunos: list[dict] = []
    vistos: set[str] = set()
    for cb in soup.select("input[name='pessoas[]']"):
        ra = (cb.get("value") or "").strip()
        if not ra or ra in vistos:
            continue
        vistos.add(ra)
        tr = cb.find_parent("tr")
        texto = tr.get_text(" ", strip=True) if tr else ""
        # formato: "453563 - Nome Completo email@x.com"
        m = re.match(r"^(\d+)\s*-\s*(.+?)\s+(\S+@\S+)\s*$", texto)
        if m:
            nome, email = m.group(2).strip(), m.group(3).strip()
        else:
            partes = texto.split()
            email = next((p for p in partes if "@" in p), "")
            nome = texto
            if email:
                nome = texto.replace(email, "").strip(" -")
            nome = re.sub(rf"^{ra}\s*-\s*", "", nome).strip()
        # dof do onclick sendmailAddOferta(DOF)
        dof = ""
        onclick = cb.get("onclick") or ""
        m_dof = re.search(r"sendmailAddOferta\((\d+)\)", onclick)
        if m_dof:
            dof = m_dof.group(1)
        alunos.append({"ra": ra, "nome": nome, "email": email, "dof": dof or (dofs[0] if len(dofs) == 1 else "")})
    return alunos


def buscar_alunos_mensagem(
    session: Session,
    disciplinas: str | list[str],
    termo: str,
) -> list[dict]:
    """Filtra alunos da turma por RA, nome ou e-mail (case-insensitive)."""
    termo = termo.strip().lower()
    return [
        a for a in listar_alunos_para_mensagem(session, disciplinas)
        if termo in a["ra"].lower()
        or termo in a["nome"].lower()
        or termo in a.get("email", "").lower()
    ]


def _remetente_padrao(html: str) -> str:
    soup = _soup(html)
    sel = soup.find("select", {"name": "remetente"})
    if not sel:
        return ""
    selected = sel.find("option", selected=True) or sel.find("option")
    return selected.get("value", "") if selected else ""


def _enviar_mensagem_composta(
    session: Session,
    html_compose: str,
    assunto: str,
    mensagem: str,
    remetente: str | None = None,
) -> dict:
    """Conclui o envio a partir da tela sendmail3 (sessão já com destinatários)."""
    remetente = remetente or _remetente_padrao(html_compose)
    if not remetente:
        raise RuntimeError("Não foi possível obter o remetente na tela de composição.")
    if not assunto or not mensagem or len(mensagem.strip()) <= 5:
        raise ValueError("Assunto e mensagem (com mais de 5 caracteres) são obrigatórios.")

    m = re.search(r"Adicionados\s+(\d+)\s+e-mails", html_compose, re.I)
    n_dest = int(m.group(1)) if m else 0

    resp = session.post(
        f"{BASE_URL}{MODULOS['mensagem_compor']}",
        data={
            "action":    "enviar",
            "origem":    "S",
            "remetente": remetente,
            "assunto":   assunto,
            "mensagem":  mensagem,
            "adicionais": "",
        },
        allow_redirects=True,
    )
    texto = _soup(resp.text).get_text(" ", strip=True)
    ok = resp.status_code == 200 and not re.search(r"erro|falha|obrigat", texto, re.I)
    # sucesso típico: volta para lista ou mensagem de confirmação
    if "sendmail.jspa" in resp.url or "enviad" in texto.lower() or "sucesso" in texto.lower():
        ok = True
    return {
        "sucesso":       ok,
        "status_code":   resp.status_code,
        "destinatarios": n_dest,
        "url":           resp.url,
        "mensagem":      texto[:300],
    }


def enviar_mensagem_turmas(
    session: Session,
    disciplinas: str | list[str],
    assunto: str,
    mensagem: str,
    remetente: str | None = None,
) -> dict:
    """Envia mensagem do portal para todos os alunos das turmas (DOF/nome)."""
    dofs = _resolver_dofs(session, disciplinas)
    resp = session.post(
        f"{BASE_URL}{MODULOS['mensagem_compor']}",
        data={"origem": "D", "discturma[]": dofs},
        allow_redirects=True,
    )
    return _enviar_mensagem_composta(session, resp.text, assunto, mensagem, remetente)


def enviar_mensagem_alunos(
    session: Session,
    alunos: str | list[str],
    assunto: str,
    mensagem: str,
    disciplinas: str | list[str] | None = None,
    remetente: str | None = None,
) -> dict:
    """Envia mensagem acadêmica do portal para alunos específicos (por RA).

    Args:
        alunos:       RA ou lista de RAs.
        assunto:      assunto da mensagem.
        mensagem:     corpo (HTML simples ou texto).
        disciplinas:  DOF/nome das turmas onde buscar os RAs.
                      Se omitido, tenta em todas as turmas do período.
        remetente:    valor completo do select (opcional).

    Returns:
        dict com {sucesso, destinatarios, status_code, ...}
    """
    ras = set(_as_list(alunos))
    if not ras:
        raise ValueError("Informe ao menos um RA.")

    if disciplinas is None:
        turmas = listar_turmas_mensagem(session)
        dofs = [t["dof"] for t in turmas if t.get("dof")]
    else:
        dofs = _resolver_dofs(session, disciplinas)

    # 1) abre lista de alunos das turmas
    resp2 = session.post(
        f"{BASE_URL}{MODULOS['mensagem_selecionar']}",
        data={"origem": "D", "discturma[]": dofs},
        allow_redirects=True,
    )
    soup2 = _soup(resp2.text)
    selecionados: list[str] = []
    ofertas: list[str] = []
    for cb in soup2.select("input[name='pessoas[]']"):
        ra = (cb.get("value") or "").strip()
        if ra not in ras:
            continue
        selecionados.append(ra)
        m_dof = re.search(r"sendmailAddOferta\((\d+)\)", cb.get("onclick") or "")
        if m_dof:
            ofertas.append(m_dof.group(1))

    if not selecionados:
        raise ValueError(
            f"Nenhum dos RAs {sorted(ras)} foi encontrado nas turmas informadas."
        )

    ofertas_str = "".join(f"{o};" for o in dict.fromkeys(ofertas))
    resp3 = session.post(
        f"{BASE_URL}{MODULOS['mensagem_compor']}",
        data={
            "origem":    "A",
            "pessoas[]": selecionados,
            "ofertas":   ofertas_str,
        },
        allow_redirects=True,
    )
    return _enviar_mensagem_composta(session, resp3.text, assunto, mensagem, remetente)


def enviar_notificacao_on(
    session: Session,
    mensagem: str,
    disciplinas: str | list[str],
    titulo: str = "",
    tipo: str = "INFORMACAO",
) -> dict:
    """Envia notificação push via app Unoesc ON.

    Args:
        mensagem:    texto da notificação.
        disciplinas: DOF ou nome/código (ou lista).
        titulo:      título curto (opcional).
        tipo:        INFORMACAO | ALERTA | ERRO | SUCESSO.

    Returns:
        dict com {sucesso, mensagem, status_code, ...}
    """
    dofs = _resolver_dofs(session, disciplinas)
    # Carrega metadados do formulário (remetente, email, etc.)
    resp = _get(session, "notificacao_on")
    soup = _soup(resp.text)

    def _val(name: str, default: str = "") -> str:
        el = soup.find("input", {"name": name})
        return el.get("value", default) if el else default

    payload = {
        "origem":         _val("origem", "PROFESSOR"),
        "remetente":      _val("remetente"),
        "remetenteEmail": _val("remetenteEmail"),
        "titulo":         titulo or mensagem[:60],
        "mensagem":       mensagem,
        "tipo":           tipo,
        "campus":         _val("campus"),
        "curso":          _val("curso"),
        "cursoNivel":     _val("cursoNivel"),
        "perfil":         _val("perfil", "ESTUDANTE"),
        "filtro":         _val("filtro", "1"),
        "ofertas":        dofs,
    }
    r = session.post(
        f"{BASE_URL}{MODULOS['notificacao_on']}?action=sendNotification",
        json=payload,
        headers={"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"},
        allow_redirects=True,
    )
    msg = ""
    try:
        body = r.json()
        msg = body.get("message") or str(body)
    except Exception:
        msg = r.text[:300]
    return {
        "sucesso":     r.status_code == 200,
        "status_code": r.status_code,
        "mensagem":    msg,
        "ofertas":     dofs,
    }


def comunicar_estudantes(
    session: Session,
    disciplinas: str | list[str],
    mensagem: str,
    assunto: str | None = None,
    alunos: str | list[str] | None = None,
    canais: tuple[str, ...] = ("portal", "push"),
    titulo_push: str = "",
    tipo_push: str = "INFORMACAO",
) -> dict:
    """Envia aviso por mensagem do portal e/ou push Unoesc ON.

    Args:
        disciplinas: DOF ou nome da disciplina (ou lista).
        mensagem:    texto do aviso.
        assunto:     assunto da mensagem do portal (obrigatório se canal portal).
        alunos:      se informado, mensagem do portal vai só para esses RAs.
                     Push ON continua por disciplina (limitação do portal).
        canais:      subset de ('portal', 'push').

    Returns:
        dict com resultados por canal.
    """
    resultado: dict = {"portal": None, "push": None}
    if "portal" in canais:
        if not assunto:
            raise ValueError("Informe 'assunto' para o canal portal.")
        if alunos:
            resultado["portal"] = enviar_mensagem_alunos(
                session, alunos=alunos, assunto=assunto, mensagem=mensagem,
                disciplinas=disciplinas,
            )
        else:
            resultado["portal"] = enviar_mensagem_turmas(
                session, disciplinas=disciplinas, assunto=assunto, mensagem=mensagem,
            )
    if "push" in canais:
        resultado["push"] = enviar_notificacao_on(
            session, mensagem=mensagem, disciplinas=disciplinas,
            titulo=titulo_push or (assunto or ""),
            tipo=tipo_push,
        )
    return resultado


# ── Ocorrências ───────────────────────────────────────────────────────────────

def listar_ocorrencias(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Lista ocorrências/observações lançadas sobre estudantes.

    Returns:
        list[dict] com aluno, data e descrição.
    """
    params = {"selAnoPeriodo": ano_periodo} if ano_periodo else None
    resp = _get(session, "ocorrencias", params)
    return _tabela(_soup(resp.text))


# ── Relatórios ────────────────────────────────────────────────────────────────

def relatorio_perfil(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Retorna relatório de perfil dos estudantes."""
    params = {"selAnoPeriodo": ano_periodo} if ano_periodo else None
    resp = _get(session, "relatorio_perfil", params)
    return _tabela(_soup(resp.text))


def relatorio_telefones(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Retorna lista de telefones dos estudantes."""
    params = {"selAnoPeriodo": ano_periodo} if ano_periodo else None
    resp = _get(session, "relatorio_telefones", params)
    return _tabela(_soup(resp.text))


def relatorio_assinaturas(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Retorna relatório de assinaturas de presença."""
    params = {"selAnoPeriodo": ano_periodo} if ano_periodo else None
    resp = _get(session, "relatorio_assinaturas", params)
    return _tabela(_soup(resp.text))


# ── Notas — Importação do diário ─────────────────────────────────────────────

def listar_avaliacoes_diario(session: Session, dof: str) -> list[dict]:
    """Lista as avaliações disponíveis no diário de classe de uma disciplina.

    Cada avaliação pode receber notas via importar_notas_diario().

    Args:
        dof: código DOF da disciplina (campo 'dof' de listar_disciplinas).

    Returns:
        list[dict]: [{nome, cod_tipo_nota, avaliacao, nota}, ...]
          - nome:          ex. 'A1/01', 'A1/02', 'A1/03'
          - cod_tipo_nota: código interno do tipo de nota
          - avaliacao:     sequência da avaliação
          - nota:          sequência da nota dentro da avaliação
    """
    resp = session.post(
        f"{BASE_URL}{MODULOS['diario_notas']}",
        data={"action": "getNotas", "dof": dof},
    )
    padrao = re.compile(
        r"openImportacaoNotasMoodlerooms\(\s*['\"]?(\d+)['\"]?\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*['\"]([^'\"]+)['\"]"
    )
    vistos = set()
    avaliacoes = []
    for m in padrao.finditer(resp.text):
        _, cod_tipo_nota, seq_aval, seq_nota, nome = m.groups()
        chave = (cod_tipo_nota, seq_aval, seq_nota)
        if chave not in vistos:
            vistos.add(chave)
            avaliacoes.append({
                "nome":          nome,
                "cod_tipo_nota": cod_tipo_nota,
                "avaliacao":     seq_aval,
                "nota":          seq_nota,
            })
    return avaliacoes


def importar_notas_diario(
    session: Session,
    dof: str,
    csv_path: str,
    avaliacao: str | int | None = None,
    nome_avaliacao: str | None = None,
) -> dict:
    """Importa notas de um CSV no formato do Portal para o diário de classe.

    O CSV deve ter o formato:
        Usuário,Atividade,Avaliação,Tipo de atividade
        NOME ALUNO,ATIVIDADE AVALIATIVA 3,10.00,Tarefa

    Use grades.exportar_notas_para_portal() para gerar o CSV a partir do Moodle.

    ATENÇÃO: A importação substitui quaisquer notas já lançadas.
    Estudantes ausentes do CSV recebem nota 0 automaticamente.

    Args:
        dof:            código DOF da disciplina.
        csv_path:       caminho do arquivo CSV.
        avaliacao:      sequência da avaliação a importar (ex. 1, 2, 3).
                        None = usa a primeira avaliação disponível.
        nome_avaliacao: filtra por nome (ex. 'A1/03'). Alternativa a avaliacao.

    Returns:
        dict com {sucesso: bool, status_code: int, mensagem: str, avaliacao: dict}
    """
    avals = listar_avaliacoes_diario(session, dof)
    if not avals:
        raise RuntimeError(f"Nenhuma avaliação encontrada no diário para dof={dof}.")

    if nome_avaliacao:
        aval = next((a for a in avals if nome_avaliacao.lower() in a["nome"].lower()), None)
        if not aval:
            nomes = [a["nome"] for a in avals]
            raise ValueError(f"Avaliação '{nome_avaliacao}' não encontrada. Disponíveis: {nomes}")
    elif avaliacao is not None:
        aval = next((a for a in avals if a["avaliacao"] == str(avaliacao)), None)
        if not aval:
            raise ValueError(f"Avaliação sequência={avaliacao} não encontrada em {[a['avaliacao'] for a in avals]}")
    else:
        aval = avals[0]

    with open(csv_path, "rb") as f:
        conteudo = f.read()

    nome_arquivo = os.path.basename(csv_path)
    # Parâmetros duplicados como query string E no corpo multipart — servidores
    # Java antigos (JSP/Servlet sem configuração multipart) ignoram parâmetros
    # de formulário quando a requisição é multipart, mas leem a query string.
    qs_params = {
        "action":        "executeImportacao",
        "codDof":        dof,
        "codTipoNota":   aval["cod_tipo_nota"],
        "avaliacao":     aval["avaliacao"],
        "nota":          aval["nota"],
        "nomeAvaliacao": aval["nome"],
    }
    resp = session.post(
        f"{BASE_URL}{MODULOS['diario_arquivo']}",
        params=qs_params,
        data=qs_params,
        files={"file": (nome_arquivo, conteudo, "text/csv")},
        allow_redirects=True,
    )

    soup = _soup(resp.text)
    msg_elem = (
        soup.find(class_=re.compile(r"success|erro|alert|mensagem|info", re.I))
        or soup.find("h2")
        or soup.find("p")
    )
    mensagem = msg_elem.get_text(strip=True) if msg_elem else resp.text[:300]

    return {
        "sucesso":    resp.status_code in (200, 302),
        "status_code": resp.status_code,
        "mensagem":   mensagem,
        "avaliacao":  aval,
    }


# ── Diário — lançamento direto de notas ──────────────────────────────────────

def extrair_mapa_alunos_diario(session: Session, dof: str) -> list[dict]:
    """Retorna lista de alunos do diário com seus identificadores internos.

    Consulta a tabela de notas do diário e extrai os dados de cada aluno
    a partir dos IDs dos spans e do conteúdo das células de cabeçalho.

    Args:
        dof: código DOF da disciplina.

    Returns:
        list[dict]: [{ra, nome, cod_adm, notas_atuais}]
          - ra:           matrícula do aluno (ex. '445509')
          - nome:         nome completo em maiúsculas (ex. 'VINICIOS ANDREI MENSEN')
          - cod_adm:      ID interno do vínculo aluno-disciplina (ex. '10128571')
          - notas_atuais: dict com médias e status extraídos dos spans
    """
    resp = session.post(
        f"{BASE_URL}{MODULOS['diario_notas']}",
        data={"action": "getNotas", "dof": dof},
    )
    html = resp.text
    soup = _soup(html)

    # Coleta cod_adm únicos a partir dos spans de média/faltas/status
    # Formato: <span id="<codAdm>-<codTipoNota>"> ou <span id="<codAdm>-faltas">
    cod_adms_ordem = []
    cod_adms_vistos = set()
    for span in soup.find_all("span", id=re.compile(r"^\d+-")):
        sid = span.get("id", "")
        parts = sid.split("-", 1)
        cod_adm = parts[0]
        if cod_adm and cod_adm not in cod_adms_vistos:
            cod_adms_vistos.add(cod_adm)
            cod_adms_ordem.append(cod_adm)

    # Extrai notas atuais por cod_adm
    notas_por_adm: dict[str, dict] = {ca: {} for ca in cod_adms_ordem}
    for span in soup.find_all("span", id=re.compile(r"^\d+-")):
        sid = span.get("id", "")
        parts = sid.split("-", 1)
        if len(parts) == 2 and parts[0] in notas_por_adm:
            notas_por_adm[parts[0]][parts[1]] = span.get_text(strip=True)

    # Extrai RA + nome das células <th> que seguem o padrão RA(5-7 dígitos)+NOME
    ra_nome_list: list[tuple[str, str]] = []
    for th in soup.find_all("th"):
        texto = th.get_text(strip=True)
        m = re.match(r"^(\d{5,7})(.+)$", texto)
        if m:
            ra_nome_list.append((m.group(1), m.group(2).strip()))

    # Monta a lista final combinando a ordem de cod_adm com ra/nome
    alunos = []
    for i, cod_adm in enumerate(cod_adms_ordem):
        if i < len(ra_nome_list):
            ra, nome = ra_nome_list[i]
        else:
            ra, nome = "", ""
        alunos.append({
            "ra":           ra,
            "nome":         nome,
            "cod_adm":      cod_adm,
            "notas_atuais": notas_por_adm.get(cod_adm, {}),
        })
    return alunos


def lancar_notas_diario(
    session: Session,
    dof: str,
    notas: dict,
    avaliacao: str | int = 3,
    cod_tipo_nota: str = "24",
    nota_seq: str = "1",
) -> dict:
    """Lança notas diretamente no diário via saveNota (uma por vez).

    Estratégia:
    1. Busca HTML da tabela de notas (action=getNotas)
    2. Extrai (cod_adm, ra, nome) de cada aluno pelos span IDs e células <th>
    3. Mapeia RA/nome → valor da nota a lançar
    4. Tenta descobrir o cn (codNotaEditada) para cada aluno:
       a. Busca inputs com id numérico no HTML
       b. Tenta cod_adm diretamente
       c. Tenta cod_adm + "-" + cod_tipo_nota + "-" + avaliacao + "-" + nota_seq
    5. Chama saveNota para cada aluno

    Args:
        dof:           código DOF da disciplina.
        notas:         {RA_ou_nome: valor_nota} — RA em string ou nome completo.
        avaliacao:     sequência da avaliação (ex. 3 para A1/03).
        cod_tipo_nota: código do tipo de nota (padrão '24').
        nota_seq:      sequência da nota dentro da avaliação (padrão '1').

    Returns:
        dict com {total, sucesso, falha, nao_encontrados, resultados}
          - resultados: list[dict] com {ra, nome, cn, nota, sucesso, resposta}
    """
    avaliacao = str(avaliacao)

    # 1. Busca e parseia a tabela de notas
    resp = session.post(
        f"{BASE_URL}{MODULOS['diario_notas']}",
        data={"action": "getNotas", "dof": dof},
    )
    html = resp.text
    soup = _soup(html)

    # 2. Extrai alunos (cod_adm + ra + nome)
    alunos = extrair_mapa_alunos_diario(session, dof)

    # Constrói índices de busca normalizados
    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip().upper()

    idx_ra:   dict[str, dict] = {a["ra"]: a for a in alunos if a["ra"]}
    idx_nome: dict[str, dict] = {_norm(a["nome"]): a for a in alunos if a["nome"]}
    idx_adm:  dict[str, dict] = {a["cod_adm"]: a for a in alunos}

    # 3. Descobre inputs numéricos no HTML para mapear cod_adm → cn
    #    O HTML do portal tem inputs <input id="<cn>" ...> dentro de cada linha
    cn_por_adm: dict[str, str] = {}
    for inp in soup.find_all("input", id=re.compile(r"^\d+")):
        inp_id = inp.get("id", "")
        # Tenta associar o input ao cod_adm da linha procurando no pai
        parent_html = str(inp.parent) if inp.parent else ""
        for cod_adm in idx_adm:
            if cod_adm in parent_html and cod_adm not in cn_por_adm:
                cn_por_adm[cod_adm] = inp_id
                break

    def _cn_para(aluno: dict) -> str:
        """Determina o melhor candidato de cn para um aluno."""
        cod_adm = aluno["cod_adm"]
        # a) Input encontrado no HTML
        if cod_adm in cn_por_adm:
            return cn_por_adm[cod_adm]
        # b) cod_adm diretamente
        return cod_adm

    def _cn_alternativas(aluno: dict) -> list[str]:
        """Lista de cn a tentar em ordem de preferência."""
        cod_adm = aluno["cod_adm"]
        candidatos = []
        if cod_adm in cn_por_adm:
            candidatos.append(cn_por_adm[cod_adm])
        candidatos.append(cod_adm)
        candidatos.append(f"{cod_adm}-{cod_tipo_nota}-{avaliacao}-{nota_seq}")
        # deduplica mantendo ordem
        vistos: set[str] = set()
        result = []
        for c in candidatos:
            if c not in vistos:
                vistos.add(c)
                result.append(c)
        return result

    # 4. Para cada aluno em notas, tenta saveNota
    resultados = []
    n_sucesso = 0
    nao_encontrados = []

    for chave_orig, valor_nota in notas.items():
        chave = _norm(str(chave_orig))

        # Tenta encontrar o aluno: primeiro por RA, depois por nome
        aluno = idx_ra.get(chave) or idx_nome.get(chave)
        if aluno is None:
            # Busca parcial por nome
            aluno = next(
                (a for nome_idx, a in idx_nome.items() if chave in nome_idx or nome_idx in chave),
                None,
            )

        if aluno is None:
            nao_encontrados.append(str(chave_orig))
            resultados.append({
                "chave":   str(chave_orig),
                "ra":      None,
                "nome":    None,
                "cn":      None,
                "nota":    valor_nota,
                "sucesso": False,
                "resposta": "Aluno não encontrado no diário",
            })
            continue

        # Normaliza o valor da nota (portal usa vírgula como separador decimal)
        try:
            vn = f"{float(str(valor_nota).replace(',', '.')):.1f}".replace(".", ",")
        except (ValueError, TypeError):
            vn = str(valor_nota)

        # Tenta cada cn candidato
        sucesso_nota = False
        cn_usado = None
        resposta_texto = ""

        for cn in _cn_alternativas(aluno):
            r = session.post(
                f"{BASE_URL}{MODULOS['diario_notas']}",
                data={"action": "saveNota", "cn": cn, "vn": vn},
                allow_redirects=True,
            )
            resposta_texto = r.text.strip()

            # Considera sucesso se a resposta contém um número (média atualizada)
            # ou é "ok" ou similar
            if re.search(r"^\d+([.,]\d+)?$", resposta_texto) or resposta_texto.lower() in ("ok", "true", "1", "sucesso"):
                sucesso_nota = True
                cn_usado = cn
                break
            # Se a resposta contiver "erro" ou "error" em qualquer forma, continua tentando
            # caso contrário, mantém o último cn tentado como referência
            cn_usado = cn

        if sucesso_nota:
            n_sucesso += 1

        resultados.append({
            "chave":   str(chave_orig),
            "ra":      aluno["ra"],
            "nome":    aluno["nome"],
            "cod_adm": aluno["cod_adm"],
            "cn":      cn_usado,
            "nota":    vn,
            "sucesso": sucesso_nota,
            "resposta": resposta_texto,
        })

    n_total = len(notas)
    return {
        "total":           n_total,
        "sucesso":         n_sucesso,
        "falha":           n_total - n_sucesso - len(nao_encontrados),
        "nao_encontrados": nao_encontrados,
        "resultados":      resultados,
    }


# ── Horários ──────────────────────────────────────────────────────────────────

def quadro_horarios(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Retorna quadro de horários do professor.

    Returns:
        list[dict] com dia, horário e disciplina.
    """
    params = {"selAnoPeriodo": ano_periodo, "tipRel": "pessoa"}
    resp = _get(session, "quadro_horarios", params)
    return _tabela(_soup(resp.text))
