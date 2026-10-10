"""
Funções para o Moodle ON UNOESC (on.unoesc.edu.br).

Cobre: acesso SSO ao curso, seções, atividades (tarefas, quizzes,
fóruns, recursos), busca e download de arquivos.

Escrita de atividades segue o padrão do py-moodle
(``update_generic_module``): GET ``modedit.php?update=…``, preserva o
formulário atual e aplica só os campos informados. Nunca apaga.
"""
import re
import os
from datetime import date, datetime
from bs4 import BeautifulSoup
from requests import Session
from .auth import BASE_URL

MOODLE_BASE = "https://on.unoesc.edu.br"

# Prefixos de data/hora do mform Moodle (assign, quiz, fórum, …)
_PREFIXOS_DATA_MOODLE = (
    "allowsubmissionsfromdate",
    "duedate",
    "cutoffdate",
    "gradingduedate",
    "timeopen",
    "timeclose",
    "assesstimestart",
    "assesstimefinish",
)


def _soup(html):
    return BeautifulSoup(html, "html.parser")


# ── Acesso ao curso ───────────────────────────────────────────────────────────

def open_course(session: Session, dof: str) -> tuple[Session, str]:
    """Autentica no Moodle via SSO a partir do DOF da discipline.

    O SSO usa JWT gerado pelo portal UNOESC. A sessão HTTP é compartilhada,
    portanto a mesma session serve para portal e Moodle após esta chamada.

    Args:
        dof: identificador da discipline (obtido via portal.list_disciplines).

    Returns:
        (session, course_id): sessão autenticada e ID do curso no Moodle.
    """
    resp_link = session.post(
        f"{BASE_URL}/portal/modules/portal/moodleRooms.jspa",
        data={"action": "criarLinkMoodleRooms", "dof": dof},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    url = resp_link.json().get("url")
    if not url:
        raise RuntimeError("Não foi possível gerar o link SSO para o Moodle.")
    resp = session.get(url, allow_redirects=True)
    m = re.search(r"id=(\d+)", resp.url)
    return session, m.group(1) if m else None


# ── Navegação ─────────────────────────────────────────────────────────────────

def list_sections(session: Session, course_id: str) -> list[dict]:
    """Lista todas as seções do curso.

    Returns:
        list[dict]: [{nome, section_id, url}, ...]
          Exemplos de nome: 'Apresentação', 'Aula - 09/02/2026', 'Avaliação A2'
    """
    resp = session.get(f"{MOODLE_BASE}/course/view.php?id={course_id}")
    matches = re.findall(
        r'<a href="(https://on\.unoesc\.edu\.br/course/section\.php\?id=(\d+))">(.*?)</a>',
        resp.text, re.DOTALL,
    )
    result = []
    for url, sid, nome in matches:
        nome = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", nome)).strip()
        result.append({"nome": nome, "section_id": sid, "url": url})
    return result


def find_section(session: Session, course_id: str, termo: str) -> dict | None:
    """Busca seção por nome parcial (case-insensitive).

    Args:
        termo: ex. '27/04', 'material didático', 'avaliação'

    Returns:
        dict com {nome, section_id, url} ou None.
    """
    termo = termo.lower()
    for s in list_sections(session, course_id):
        if termo in s["nome"].lower():
            return s
    return None


def find_activity(
    session: Session,
    section_id: str,
    termo: str,
    tipo: str | None = None,
) -> dict | None:
    """Busca atividade por nome parcial (case-insensitive) em uma seção.

    Args:
        termo: ex. 'Prova Objetiva', 'ATIVIDADE AVALIATIVA 3'.
        tipo:  filtra por tipo Moodle ('quiz', 'assign', 'lti', ...). None = qualquer.

    Returns:
        dict com {nome, tipo, activity_id, url} ou None.
    """
    termo = termo.lower()
    for a in list_activities(session, section_id):
        if tipo and a["tipo"] != tipo:
            continue
        if termo in a["nome"].lower():
            return a
    return None


def list_activities(session: Session, section_id: str) -> list[dict]:
    """Lista atividades de uma seção.

    Returns:
        list[dict]: [{nome, tipo, activity_id, url}, ...]
          Tipos possíveis: 'assign' (tarefa), 'quiz' (questionário),
          'resource' (arquivo), 'url' (link), 'hsuforum' (fórum), 'lti'.
    """
    resp = session.get(f"{MOODLE_BASE}/course/section.php?id={section_id}")
    html = resp.text
    result, seen = [], set()

    # 1. Atividades visíveis na seção (instancename)
    matches = re.findall(
        r'<a[^>]+href="(https://on\.unoesc\.edu\.br/mod/([^/]+)/[^"?]+\?id=(\d+))[^"]*"[^>]*>'
        r'.*?<span[^>]*class="[^"]*instancename[^"]*"[^>]*>(.*?)</span>',
        html, re.DOTALL,
    )
    for url, tipo, aid, nome in matches:
        nome = re.sub(r"<[^>]+>", "", nome).strip()
        key = (tipo, aid)
        if key not in seen:
            seen.add(key)
            result.append({"nome": nome, "tipo": tipo, "activity_id": aid, "url": url})

    # 2. Fallback: links mod/* na seção sem instancename (ex.: quiz oculto atrás de LTI)
    for url in re.findall(r'href="(https://on\.unoesc\.edu\.br/mod/[^"]+)"', html):
        m = re.search(r'/mod/([^/]+)/[^"?]+\?id=(\d+)', url)
        if not m:
            continue
        tipo, aid = m.group(1), m.group(2)
        if tipo == "lti" and "coursetools" in url:
            continue
        key = (tipo, aid)
        if key in seen:
            continue
        seen.add(key)
        nome = ""
        chunk = html[max(0, html.find(url) - 400): html.find(url) + 400]
        nm = re.search(r'instancename[^>]*>(.*?)</span>', chunk, re.DOTALL)
        if nm:
            nome = re.sub(r"<[^>]+>", "", nm.group(1)).strip()
        if not nome:
            vr = session.get(url, allow_redirects=True)
            title = re.search(r"<title>(.*?)</title>", vr.text, re.I)
            if title:
                nome = re.sub(r"\s*\|\s*On$", "", title.group(1)).strip()
                nome = re.sub(r"^[^:]+:\s*", "", nome, count=1)
        result.append({"nome": nome or f"{tipo} {aid}", "tipo": tipo, "activity_id": aid, "url": url})

    return result


def classify_section(nome: str) -> str:
    """Classifica o papel típico de uma seção da trilha pelo nome.

    Returns:
        Um de: ``presentation``, ``plan``, ``unit``, ``week``,
        ``lesson``, ``material``, ``assessment``, ``support``, ``forum``,
        ``other``.
    """
    n = (nome or "").strip()
    low = n.lower()
    if re.search(r"apresenta|boas.?vindas|in[ií]cio", low):
        return "presentation"
    if re.search(r"plano\s*de\s*ensino|schedule", low):
        return "plan"
    if re.search(r"^unidade\b|unidade\s*\d+", low):
        return "unit"
    if re.search(r"^semana\s*\d+", low):
        return "week"
    if re.search(r"^aula\b", low) or re.search(r"aula\s*-?\s*\d{1,2}/\d{1,2}", low):
        return "lesson"
    if re.search(r"material\s*did", low):
        return "material"
    if re.search(r"avalia|exame\s*\|\s*a2|\ba2\b|exame\s*final", low):
        return "assessment"
    if re.search(r"apoio|tutorial", low):
        return "support"
    if re.search(r"tira.?d[uú]vida|f[oó]rum", low):
        return "forum"
    return "other"


def _extract_section_date(nome: str) -> str | None:
    """Extrai a primeira data dd/mm/yyyy (ou dd/mm/yy) do nome da seção."""
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", nome or "")
    if not m:
        return None
    d, mo, y = m.group(1).split("/")
    if len(y) == 2:
        y = "20" + y
    return f"{int(d):02d}/{int(mo):02d}/{y}"


def get_course_structure(
    session: Session,
    course_id: str,
    *,
    include_activities: bool = False,
) -> dict:
    """Lê a estrutura atual da trilha no Moodle (somente leitura).

    Args:
        course_id: ID do curso Moodle.
        include_activities: se True, busca atividades de cada seção.

    Returns:
        dict: {
          course_id, n_sections, pattern, padroes,
          secoes: [{nome, section_id, url, papel, data, atividades?}]
        }

        ``pattern`` resume o modelo dominante: ``ead_semanas``,
        ``presencial_aulas`` ou ``misto``.
    """
    from collections import Counter

    secoes_raw = list_sections(session, course_id)
    secoes = []
    for s in secoes_raw:
        papel = classify_section(s["nome"])
        item = {
            "nome": s["nome"],
            "section_id": s["section_id"],
            "url": s["url"],
            "papel": papel,
            "data": _extract_section_date(s["nome"]),
        }
        if include_activities:
            try:
                acts = list_activities(session, s["section_id"])
            except Exception as exc:  # noqa: BLE001 - leitura best-effort
                acts = []
                item["activities_error"] = str(exc)
            item["activities"] = acts
            item["n_activities"] = len(acts)
            item["activity_types"] = dict(Counter(a["tipo"] for a in acts))
        secoes.append(item)

    contagem = Counter(s["papel"] for s in secoes)
    if contagem.get("week", 0) >= 2 and contagem.get("week", 0) >= contagem.get("lesson", 0):
        pattern = "ead_weeks"
    elif contagem.get("lesson", 0) >= 2:
        pattern = "in_person_lessons"
    elif contagem.get("week", 0) and contagem.get("lesson", 0):
        pattern = "mixed"
    else:
        pattern = "mixed" if len(secoes) else "empty"

    return {
        "course_id": course_id,
        "n_sections": len(secoes),
        "pattern": pattern,
        "padroes": dict(contagem),
        "sections": secoes,
    }


# ── Escrita (dry_run=True por padrão; nunca apaga) ─────────────────────────────

_TIPOS_ATIVIDADE = ("url", "folder", "hsuforum", "assign", "quiz")


def _get_sesskey(session: Session, course_id: str) -> str:
    """Extrai sesskey da página do curso."""
    resp = session.get(f"{MOODLE_BASE}/course/view.php", params={"id": course_id})
    m = re.search(r'name="sesskey"\s+value="([^"]+)"', resp.text)
    if not m:
        m = re.search(r'"sesskey"\s*:\s*"([^"]+)"', resp.text)
    if not m:
        raise RuntimeError("sesskey não encontrado na página do curso Moodle.")
    return m.group(1)


def _parse_mform(html: str, form_action_substr: str | None = None) -> tuple[object, dict[str, str]]:
    """Extrai action e campos de um mform Moodle.

    Segue a lógica do py-moodle ``_extract_modedit_form_data``: checkboxes/
    radios só entram se marcados; ``file`` é ignorado (o browser também não
    reenvia o valor existente).

    Returns:
        (form_tag, data_dict)
    """
    soup = _soup(html)
    form = None
    if form_action_substr:
        form = soup.find("form", action=re.compile(re.escape(form_action_substr), re.I))
    if form is None:
        form = soup.find("form", id=re.compile(r"mform", re.I))
    if form is None:
        form = soup.find("form", class_=re.compile(r"mform", re.I))
    if form is None:
        raise RuntimeError("Formulário Moodle (mform) não encontrado.")

    data: dict[str, str] = {}
    for el in form.find_all("input"):
        name = el.get("name")
        if not name:
            continue
        tipo = (el.get("type") or "text").lower()
        if tipo in ("submit", "button", "image", "reset", "file"):
            continue
        if tipo == "checkbox":
            if el.has_attr("checked"):
                data[name] = el.get("value", "1")
            continue
        if tipo == "radio":
            if el.has_attr("checked"):
                data[name] = el.get("value", "")
            continue
        data[name] = el.get("value", "") or ""
    for el in form.find_all("textarea"):
        name = el.get("name")
        if name:
            data[name] = el.get_text() or ""
    for el in form.find_all("select"):
        name = el.get("name")
        if not name:
            continue
        if el.has_attr("multiple"):
            selecionados = [
                opt.get("value", "")
                for opt in el.find_all("option", selected=True)
            ]
            if selecionados:
                data[name] = selecionados[0]
            continue
        opt = el.find("option", selected=True) or el.find("option")
        data[name] = opt.get("value", "") if opt else ""
    return form, data


def _extract_moodle_error(html: str) -> str | None:
    """Tenta extrair message de erro da página Moodle após POST de formulário."""
    soup = _soup(html)
    for sel in (
        ".alert-danger",
        ".notifyproblem",
        "#notice .box",
        ".error",
        "[role='alert']",
    ):
        el = soup.select_one(sel)
        if el:
            txt = re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()
            if txt:
                return txt[:500]
    return None


def _parse_moodle_datetime(valor) -> datetime:
    """Converte datetime/date/str em ``datetime`` para campos Moodle.

    Strings aceitas: ``dd/mm/yyyy``, ``dd/mm/yyyy HH:MM``, ``yyyy-mm-dd``,
    ``yyyy-mm-ddTHH:MM`` / ``yyyy-mm-dd HH:MM``.
    """
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)
    if not isinstance(valor, str):
        raise TypeError(f"Data Moodle inválida: {type(valor)!r}")
    s = valor.strip()
    for fmt in (
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(
        f"Data '{valor}' não reconhecida. Use dd/mm/yyyy[ HH:MM] ou ISO."
    )


def moodle_datetime_fields(
    prefixo: str,
    valor,
    *,
    enabled: bool = True,
    hora: int | None = None,
    minuto: int | None = None,
) -> dict[str, str]:
    """Monta os campos ``prefixo[year|month|day|hour|minute|enabled]`` do mform.

    Args:
        prefixo: ex. ``duedate``, ``timeopen``, ``allowsubmissionsfromdate``.
        valor: ``datetime``, ``date`` ou string (ver ``_parse_moodle_datetime``).
            Se ``None``/``False``, desabilita o campo (``enabled=0``).
        enabled: força habilitar/desabilitar.
        hora / minuto: sobrescrevem o horário do valor.
    """
    if valor is None or valor is False:
        return {f"{prefixo}[enabled]": "0"}
    dt = _parse_moodle_datetime(valor)
    h = dt.hour if hora is None else hora
    m = dt.minute if minuto is None else minuto
    return {
        f"{prefixo}[enabled]": "1" if enabled else "0",
        f"{prefixo}[day]": str(dt.day),
        f"{prefixo}[month]": str(dt.month),
        f"{prefixo}[year]": str(dt.year),
        f"{prefixo}[hour]": str(h),
        f"{prefixo}[minute]": str(m),
    }


def _expand_activity_options(options: dict | None) -> dict[str, str]:
    """Expande atalhos de data em campos mform; demais chaves passam como string.

    Atalhos: chaves em ``_PREFIXOS_DATA_MOODLE`` com valor date/datetime/str/
    None/False → campos ``[day]/[month]/…``. Valores já no formato
    ``duedate[year]`` passam direto.
    """
    if not options:
        return {}
    out: dict[str, str] = {}
    for k, v in options.items():
        if k in _PREFIXOS_DATA_MOODLE:
            out.update(moodle_datetime_fields(k, v))
            continue
        if isinstance(v, bool):
            out[k] = "1" if v else "0"
        elif v is None:
            continue
        else:
            out[k] = str(v)
    return out


def _resolve_moodle_action(form, default_path: str) -> str:
    action = form.get("action") or default_path
    if action.startswith("/"):
        return MOODLE_BASE + action
    if not action.startswith("http"):
        return f"{MOODLE_BASE}/course/{action}"
    return action


def _set_editing_mode(
    session: Session,
    course_id: str,
    *,
    ligar: bool = True,
    dry_run: bool = True,
) -> dict:
    """Liga/desliga o modo de edição do curso."""
    sesskey = _get_sesskey(session, course_id)
    if dry_run:
        return {"success": True, "dry_run": True, "sesskey": sesskey, "edit": ligar}
    session.get(
        f"{MOODLE_BASE}/course/view.php",
        params={
            "id": course_id,
            "sesskey": sesskey,
            "edit": "on" if ligar else "off",
        },
    )
    return {"success": True, "dry_run": False, "sesskey": sesskey, "edit": ligar}


def create_section(
    session: Session,
    course_id: str,
    nome: str,
    *,
    position: int | None = None,
    dry_run: bool = True,
) -> dict:
    """Cria uma seção (tópico) no curso e define o nome.

    Não remove seções existentes. Com ``dry_run=True`` (padrão) não envia POST/GET
    de mutação.

    Args:
        course_id: ID do curso Moodle.
        nome: nome da seção.
        position: número da seção onde inserir (``insertsection``). None = ao final.
        dry_run: se True, só descreve a ação.

    Returns:
        dict com {success, dry_run, acao, nome, section_id?, position?, message?}
    """
    antes = list_sections(session, course_id)
    # ids de seção HTML (0..n-1)
    resp = session.get(f"{MOODLE_BASE}/course/view.php", params={"id": course_id})
    nums = [int(x) for x in re.findall(r'id="section-(\d+)"', resp.text)]
    ultimo = max(nums) if nums else max(0, len(antes) - 1)
    insert_at = position if position is not None else (ultimo + 1)
    sesskey = _get_sesskey(session, course_id)

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "action": "create_section",
            "nome": nome,
            "position": insert_at,
            "section_id": None,
            "message": f"Simularía inserir seção em insertsection={insert_at} e renomear para '{nome}'.",
        }

    _set_editing_mode(session, course_id, ligar=True, dry_run=False)
    session.get(
        f"{MOODLE_BASE}/course/changenumsections.php",
        params={
            "courseid": course_id,
            "insertsection": insert_at,
            "numsections": 1,
            "sesskey": sesskey,
        },
        allow_redirects=True,
    )
    depois = list_sections(session, course_id)
    ids_antes = {s["section_id"] for s in antes}
    novas = [s for s in depois if s["section_id"] not in ids_antes]
    if not novas:
        # fallback: última seção
        if len(depois) > len(antes):
            novas = depois[len(antes):]
        else:
            _set_editing_mode(session, course_id, ligar=False, dry_run=False)
            return {
                "success": False,
                "dry_run": False,
                "action": "create_section",
                "nome": nome,
                "position": insert_at,
                "message": "Seção criada não foi localizada após changenumsections.",
            }

    nova = novas[-1]
    ren = update_section(session, nova["section_id"], nome=nome, dry_run=False)
    _set_editing_mode(session, course_id, ligar=False, dry_run=False)
    return {
        "success": bool(ren.get("success")),
        "dry_run": False,
        "action": "create_section",
        "nome": nome,
        "position": insert_at,
        "section_id": nova["section_id"],
        "message": ren.get("message"),
    }


def update_section(
    session: Session,
    section_id: str,
    *,
    nome: str | None = None,
    visible: bool | None = None,
    dry_run: bool = True,
) -> dict:
    """Atualiza nome (e opcionalmente visibilidade) de uma seção. Não apaga."""
    resp = session.get(
        f"{MOODLE_BASE}/course/editsection.php",
        params={"id": section_id},
    )
    try:
        form, data = _parse_mform(resp.text, "editsection.php")
    except RuntimeError as exc:
        return {
            "success": False,
            "dry_run": dry_run,
            "action": "update_section",
            "section_id": section_id,
            "message": str(exc),
        }

    if nome is not None:
        data["name"] = nome
    # visibilidade: campo nem sempre presente; ignora se ausente
    if visible is not None and "visible" in data:
        data["visible"] = "1" if visible else "0"

    data["submitbutton"] = "Salvar alterações"
    action = form.get("action") or f"{MOODLE_BASE}/course/editsection.php"
    if action.startswith("/"):
        action = MOODLE_BASE + action

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "action": "update_section",
            "section_id": section_id,
            "nome": nome,
            "payload_fields": len(data),
            "message": f"Simularía renomear section_id={section_id} para '{nome}'.",
        }

    post = session.post(action, data=data, allow_redirects=True)
    ok = post.status_code == 200
    return {
        "success": ok,
        "dry_run": False,
        "action": "update_section",
        "section_id": section_id,
        "nome": nome,
        "status_code": post.status_code,
        "message": None if ok else f"HTTP {post.status_code}",
    }


def create_activity(
    session: Session,
    course_id: str,
    section_num: int,
    tipo: str,
    nome: str,
    *,
    intro: str | None = None,
    options: dict | None = None,
    dry_run: bool = True,
) -> dict:
    """Cria uma atividade Moodle na seção indicada.

    Tipos suportados: ``url``, ``folder``, ``hsuforum``, ``assign``, ``quiz``.
    LTI não é suportado. ``dry_run=True`` por padrão.

    Args:
        section_num: índice da seção (0 = primeira), não o section_id.
        options: extras (ex. ``{"externalurl": "https://..."}`` para url).
    """
    tipo = (tipo or "").lower().strip()
    if tipo not in _TIPOS_ATIVIDADE:
        return {
            "success": False,
            "dry_run": dry_run,
            "action": "create_activity",
            "tipo": tipo,
            "nome": nome,
            "message": f"Tipo '{tipo}' não suportado. Use: {_TIPOS_ATIVIDADE}",
        }

    options = options or {}
    resp = session.get(
        f"{MOODLE_BASE}/course/modedit.php",
        params={
            "add": tipo,
            "type": "",
            "course": course_id,
            "section": section_num,
            "return": 0,
        },
    )
    try:
        form, data = _parse_mform(resp.text, "modedit")
    except RuntimeError as exc:
        return {
            "success": False,
            "dry_run": dry_run,
            "action": "create_activity",
            "tipo": tipo,
            "nome": nome,
            "message": str(exc),
        }

    data["name"] = nome
    if "introeditor[text]" in data:
        data["introeditor[text]"] = intro or ""
    if "introeditor[format]" in data and not data.get("introeditor[format]"):
        data["introeditor[format]"] = "1"
    data["section"] = str(section_num)
    data["course"] = str(course_id)
    data["add"] = tipo
    data["modulename"] = tipo

    if tipo == "url":
        url = options.get("externalurl") or options.get("url") or "https://on.unoesc.edu.br"
        data["externalurl"] = url

    extras = _expand_activity_options(
        {k: v for k, v in options.items() if k not in ("externalurl", "url")}
    )
    data.update(extras)

    # Salvar e voltar ao curso
    data["submitbutton2"] = "Salvar e voltar ao curso"
    data.pop("submitbutton", None)

    action = _resolve_moodle_action(form, f"{MOODLE_BASE}/course/modedit.php")

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "action": "create_activity",
            "tipo": tipo,
            "nome": nome,
            "section_num": section_num,
            "payload_fields": len(data),
            "changed_fields": extras,
            "message": f"Simularía criar {tipo} '{nome}' na seção {section_num}.",
        }

    post = session.post(action, data=data, allow_redirects=True)
    # tenta extrair cmid da URL final
    m = re.search(r"[?&]id=(\d+)", post.url or "")
    activity_id = m.group(1) if m and "mod/" in (post.url or "") else None
    ok = post.status_code == 200
    erro = None if ok else f"HTTP {post.status_code}"
    if ok:
        erro_moodle = _extract_moodle_error(post.text)
        if erro_moodle and "modedit" in (post.url or ""):
            ok = False
            erro = erro_moodle
    return {
        "success": ok,
        "dry_run": False,
        "action": "create_activity",
        "tipo": tipo,
        "nome": nome,
        "section_num": section_num,
        "activity_id": activity_id,
        "status_code": post.status_code,
        "url": post.url,
        "message": erro,
    }


def update_activity(
    session: Session,
    activity_id: str | int,
    *,
    nome: str | None = None,
    intro: str | None = None,
    options: dict | None = None,
    dry_run: bool = True,
) -> dict:
    """Atualiza uma atividade existente via ``modedit.php?update=…``.

    Segue o padrão do py-moodle ``update_generic_module``: carrega o formulário
    atual (preserva todos os campos), aplica só as mudanças pedidas e POST.
    Nunca apaga a atividade. ``dry_run=True`` por padrão.

    Args:
        activity_id: cmid da atividade (``id=`` na URL ``/mod/.../view.php``).
        nome: novo nome (opcional).
        intro: novo texto do editor ``introeditor[text]`` (opcional).
        options: campos do mform a sobrescrever. Atalhos de data aceitos:
            ``duedate``, ``allowsubmissionsfromdate``, ``cutoffdate``,
            ``gradingduedate``, ``timeopen``, ``timeclose`` — valor
            ``datetime``/``date``/``"dd/mm/yyyy[ HH:MM]"``/``None`` (desliga).
            Também aceita chaves cruas (ex. ``duedate[year]``).
        dry_run: se True, não envia POST.

    Returns:
        dict com ``success``, ``dry_run``, ``acao``, ``activity_id``,
        ``changed_fields``, ``message``, …
    """
    activity_id = str(activity_id)
    extras = _expand_activity_options(options)
    if nome is None and intro is None and not extras:
        return {
            "success": True,
            "dry_run": dry_run,
            "action": "update_activity",
            "activity_id": activity_id,
            "changed_fields": {},
            "message": "Nada a atualizar.",
        }

    edit_url = f"{MOODLE_BASE}/course/modedit.php"
    resp = session.get(edit_url, params={"update": activity_id})
    try:
        form, data = _parse_mform(resp.text, "modedit")
    except RuntimeError as exc:
        erro_pagina = _extract_moodle_error(resp.text)
        return {
            "success": False,
            "dry_run": dry_run,
            "action": "update_activity",
            "activity_id": activity_id,
            "message": erro_pagina or str(exc),
        }

    antes = dict(data)
    alterados: dict[str, dict[str, str | None]] = {}

    def _set(campo: str, valor: str) -> None:
        antigo = antes.get(campo)
        if antigo == valor:
            return
        data[campo] = valor
        alterados[campo] = {"de": antigo, "para": valor}

    if nome is not None:
        _set("name", nome)
    if intro is not None and "introeditor[text]" in data:
        _set("introeditor[text]", intro)
        if "introeditor[format]" in data and not data.get("introeditor[format]"):
            _set("introeditor[format]", "1")

    for k, v in extras.items():
        _set(k, v)

    data["submitbutton2"] = "Salvar e voltar ao curso"
    data.pop("submitbutton", None)

    action = _resolve_moodle_action(form, edit_url)

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "action": "update_activity",
            "activity_id": activity_id,
            "nome": nome if nome is not None else data.get("name"),
            "changed_fields": alterados,
            "payload_fields": len(data),
            "message": (
                f"Simularía atualizar activity_id={activity_id} "
                f"({len(alterados)} campo(s))."
            ),
        }

    # Como py-moodle: sem follow redirect; 302/303 = success
    post = session.post(action, data=data, allow_redirects=False)
    if post.status_code in (302, 303):
        return {
            "success": True,
            "dry_run": False,
            "action": "update_activity",
            "activity_id": activity_id,
            "nome": data.get("name"),
            "changed_fields": alterados,
            "status_code": post.status_code,
            "location": post.headers.get("Location"),
            "message": None,
        }

    # Alguns temas devolvem 200 na própria página do curso após POST com redirect=True
    # Fallback: POST com follow se 200 sem erro de formulário
    if post.status_code == 200:
        erro = _extract_moodle_error(post.text)
        ainda_no_form = "modedit" in (post.url or "") or bool(
            _soup(post.text).find("form", action=re.compile("modedit", re.I))
        )
        if erro and ainda_no_form:
            return {
                "success": False,
                "dry_run": False,
                "action": "update_activity",
                "activity_id": activity_id,
                "changed_fields": alterados,
                "status_code": post.status_code,
                "message": erro,
            }
        if not ainda_no_form:
            return {
                "success": True,
                "dry_run": False,
                "action": "update_activity",
                "activity_id": activity_id,
                "nome": data.get("name"),
                "changed_fields": alterados,
                "status_code": post.status_code,
                "message": None,
            }

    return {
        "success": False,
        "dry_run": False,
        "action": "update_activity",
        "activity_id": activity_id,
        "changed_fields": alterados,
        "status_code": post.status_code,
        "message": (
            _extract_moodle_error(post.text)
            or f"Falha ao atualizar. HTTP {post.status_code}."
        ),
    }


# ── Tarefas (assign) ──────────────────────────────────────────────────────────

def get_assignment(session: Session, activity_id: str) -> dict:
    """Retorna detalhes de uma tarefa (assign).

    Returns:
        dict: {title, description, due, url}
    """
    resp = session.get(f"{MOODLE_BASE}/mod/assign/view.php?id={activity_id}")
    soup = _soup(resp.text)
    title   = soup.find("h2")
    description = soup.find("div", class_=re.compile("description|intro"))
    due    = soup.find(string=re.compile(r"due|due|entrega", re.I))
    return {
        "title":    title.get_text(strip=True) if title else "",
        "description": description.get_text(strip=True)[:500] if description else "",
        "due":     due.strip() if due else "",
        "url":       resp.url,
    }


# ── Questionários (quiz) ──────────────────────────────────────────────────────

def get_quiz(session: Session, activity_id: str) -> dict:
    """Retorna detalhes de um questionário (quiz).

    Returns:
        dict: {title, intro, url}
    """
    resp = session.get(f"{MOODLE_BASE}/mod/quiz/view.php?id={activity_id}")
    soup = _soup(resp.text)
    title = soup.find("h2") or soup.find("h1")
    intro  = soup.find("div", class_=re.compile("intro|description"))
    return {
        "title": title.get_text(strip=True) if title else "",
        "intro":  intro.get_text(strip=True)[:500] if intro else "",
        "url":    resp.url,
    }


# ── Fóruns (hsuforum) ─────────────────────────────────────────────────────────

def get_forum(session: Session, activity_id: str) -> dict:
    """Retorna posts de um fórum.

    Returns:
        dict: {title, posts: [{autor, corpo}, ...], url}
    """
    resp = session.get(f"{MOODLE_BASE}/mod/hsuforum/view.php?id={activity_id}")
    soup = _soup(resp.text)
    title = soup.find("h2") or soup.find("h1")
    posts  = soup.find_all("div", class_=re.compile("forumpost|post"))
    resultado = []
    for p in posts[:10]:
        autor = p.find(class_=re.compile("author|name"))
        corpo = p.find(class_=re.compile("content|message"))
        resultado.append({
            "autor": autor.get_text(strip=True) if autor else "",
            "corpo": corpo.get_text(strip=True)[:300] if corpo else "",
        })
    return {
        "title": title.get_text(strip=True) if title else "",
        "posts":  resultado,
        "url":    resp.url,
    }


# ── Recursos (resource / url) ─────────────────────────────────────────────────

def download_resource(session: Session, activity_id: str, destination: str | None = None) -> str:
    """Baixa um arquivo de recurso (tipo 'resource').

    Args:
        activity_id: ID da atividade do tipo resource.
        destination: caminho completo para salvar. None = ~/Downloads/<nome_original>.

    Returns:
        Caminho do arquivo salvo.
    """
    resp = session.get(
        f"{MOODLE_BASE}/mod/resource/view.php?id={activity_id}",
        allow_redirects=True,
    )
    content_disp = resp.headers.get("Content-Disposition", "")
    m = re.search(r'filename="?([^";\n]+)"?', content_disp)
    nome = m.group(1).strip() if m else f"recurso_{activity_id}"
    if destination is None:
        destination = os.path.expanduser(f"~/Downloads/{nome}")
    with open(destination, "wb") as f:
        f.write(resp.content)
    print(f"Arquivo salvo em: {destination}")
    return destination
