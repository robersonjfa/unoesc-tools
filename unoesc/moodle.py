"""
Funções para o Moodle ON UNOESC (on.unoesc.edu.br).

Cobre: acesso SSO ao curso, seções, atividades (tarefas, quizzes,
fóruns, recursos), busca e download de arquivos.
"""
import re
import os
from bs4 import BeautifulSoup
from requests import Session
from .auth import BASE_URL

MOODLE_BASE = "https://on.unoesc.edu.br"


def _soup(html):
    return BeautifulSoup(html, "html.parser")


# ── Acesso ao curso ───────────────────────────────────────────────────────────

def abrir_curso(session: Session, dof: str) -> tuple[Session, str]:
    """Autentica no Moodle via SSO a partir do DOF da disciplina.

    O SSO usa JWT gerado pelo portal UNOESC. A sessão HTTP é compartilhada,
    portanto a mesma session serve para portal e Moodle após esta chamada.

    Args:
        dof: identificador da disciplina (obtido via portal.listar_disciplinas).

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

def listar_secoes(session: Session, course_id: str) -> list[dict]:
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


def buscar_secao(session: Session, course_id: str, termo: str) -> dict | None:
    """Busca seção por nome parcial (case-insensitive).

    Args:
        termo: ex. '27/04', 'material didático', 'avaliação'

    Returns:
        dict com {nome, section_id, url} ou None.
    """
    termo = termo.lower()
    for s in listar_secoes(session, course_id):
        if termo in s["nome"].lower():
            return s
    return None


def buscar_atividade(
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
    for a in listar_atividades(session, section_id):
        if tipo and a["tipo"] != tipo:
            continue
        if termo in a["nome"].lower():
            return a
    return None


def listar_atividades(session: Session, section_id: str) -> list[dict]:
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


def classificar_secao(nome: str) -> str:
    """Classifica o papel típico de uma seção da trilha pelo nome.

    Returns:
        Um de: ``apresentacao``, ``plano``, ``unidade``, ``semana``,
        ``aula``, ``material``, ``avaliacao``, ``apoio``, ``forum``,
        ``outro``.
    """
    n = (nome or "").strip()
    low = n.lower()
    if re.search(r"apresenta|boas.?vindas|in[ií]cio", low):
        return "apresentacao"
    if re.search(r"plano\s*de\s*ensino|cronograma", low):
        return "plano"
    if re.search(r"^unidade\b|unidade\s*\d+", low):
        return "unidade"
    if re.search(r"^semana\s*\d+", low):
        return "semana"
    if re.search(r"^aula\b", low) or re.search(r"aula\s*-?\s*\d{1,2}/\d{1,2}", low):
        return "aula"
    if re.search(r"material\s*did", low):
        return "material"
    if re.search(r"avalia|exame\s*\|\s*a2|\ba2\b|exame\s*final", low):
        return "avaliacao"
    if re.search(r"apoio|tutorial", low):
        return "apoio"
    if re.search(r"tira.?d[uú]vida|f[oó]rum", low):
        return "forum"
    return "outro"


def _extrair_data_secao(nome: str) -> str | None:
    """Extrai a primeira data dd/mm/yyyy (ou dd/mm/yy) do nome da seção."""
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", nome or "")
    if not m:
        return None
    d, mo, y = m.group(1).split("/")
    if len(y) == 2:
        y = "20" + y
    return f"{int(d):02d}/{int(mo):02d}/{y}"


def obter_estrutura_curso(
    session: Session,
    course_id: str,
    *,
    incluir_atividades: bool = False,
) -> dict:
    """Lê a estrutura atual da trilha no Moodle (somente leitura).

    Args:
        course_id: ID do curso Moodle.
        incluir_atividades: se True, busca atividades de cada seção.

    Returns:
        dict: {
          course_id, n_secoes, padrao, padroes,
          secoes: [{nome, section_id, url, papel, data, atividades?}]
        }

        ``padrao`` resume o modelo dominante: ``ead_semanas``,
        ``presencial_aulas`` ou ``misto``.
    """
    from collections import Counter

    secoes_raw = listar_secoes(session, course_id)
    secoes = []
    for s in secoes_raw:
        papel = classificar_secao(s["nome"])
        item = {
            "nome": s["nome"],
            "section_id": s["section_id"],
            "url": s["url"],
            "papel": papel,
            "data": _extrair_data_secao(s["nome"]),
        }
        if incluir_atividades:
            try:
                acts = listar_atividades(session, s["section_id"])
            except Exception as exc:  # noqa: BLE001 - leitura best-effort
                acts = []
                item["atividades_erro"] = str(exc)
            item["atividades"] = acts
            item["n_atividades"] = len(acts)
            item["tipos_atividades"] = dict(Counter(a["tipo"] for a in acts))
        secoes.append(item)

    contagem = Counter(s["papel"] for s in secoes)
    if contagem.get("semana", 0) >= 2 and contagem.get("semana", 0) >= contagem.get("aula", 0):
        padrao = "ead_semanas"
    elif contagem.get("aula", 0) >= 2:
        padrao = "presencial_aulas"
    elif contagem.get("semana", 0) and contagem.get("aula", 0):
        padrao = "misto"
    else:
        padrao = "misto" if len(secoes) else "vazio"

    return {
        "course_id": course_id,
        "n_secoes": len(secoes),
        "padrao": padrao,
        "padroes": dict(contagem),
        "secoes": secoes,
    }


# ── Escrita (dry_run=True por padrão; nunca apaga) ─────────────────────────────

_TIPOS_ATIVIDADE = ("url", "folder", "hsuforum", "assign", "quiz")


def _obter_sesskey(session: Session, course_id: str) -> str:
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

    Returns:
        (form_tag, data_dict) — checkboxes só entram se marcados; radios só o selecionado.
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
        if tipo in ("submit", "button", "image"):
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
        opt = el.find("option", selected=True) or el.find("option")
        data[name] = opt.get("value", "") if opt else ""
    return form, data


def _ativar_modo_edicao(
    session: Session,
    course_id: str,
    *,
    ligar: bool = True,
    dry_run: bool = True,
) -> dict:
    """Liga/desliga o modo de edição do curso."""
    sesskey = _obter_sesskey(session, course_id)
    if dry_run:
        return {"sucesso": True, "dry_run": True, "sesskey": sesskey, "edit": ligar}
    session.get(
        f"{MOODLE_BASE}/course/view.php",
        params={
            "id": course_id,
            "sesskey": sesskey,
            "edit": "on" if ligar else "off",
        },
    )
    return {"sucesso": True, "dry_run": False, "sesskey": sesskey, "edit": ligar}


def criar_secao(
    session: Session,
    course_id: str,
    nome: str,
    *,
    posicao: int | None = None,
    dry_run: bool = True,
) -> dict:
    """Cria uma seção (tópico) no curso e define o nome.

    Não remove seções existentes. Com ``dry_run=True`` (padrão) não envia POST/GET
    de mutação.

    Args:
        course_id: ID do curso Moodle.
        nome: nome da seção.
        posicao: número da seção onde inserir (``insertsection``). None = ao final.
        dry_run: se True, só descreve a ação.

    Returns:
        dict com {sucesso, dry_run, acao, nome, section_id?, posicao?, mensagem?}
    """
    antes = listar_secoes(session, course_id)
    # ids de seção HTML (0..n-1)
    resp = session.get(f"{MOODLE_BASE}/course/view.php", params={"id": course_id})
    nums = [int(x) for x in re.findall(r'id="section-(\d+)"', resp.text)]
    ultimo = max(nums) if nums else max(0, len(antes) - 1)
    insert_at = posicao if posicao is not None else (ultimo + 1)
    sesskey = _obter_sesskey(session, course_id)

    if dry_run:
        return {
            "sucesso": True,
            "dry_run": True,
            "acao": "criar_secao",
            "nome": nome,
            "posicao": insert_at,
            "section_id": None,
            "mensagem": f"Simularía inserir seção em insertsection={insert_at} e renomear para '{nome}'.",
        }

    _ativar_modo_edicao(session, course_id, ligar=True, dry_run=False)
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
    depois = listar_secoes(session, course_id)
    ids_antes = {s["section_id"] for s in antes}
    novas = [s for s in depois if s["section_id"] not in ids_antes]
    if not novas:
        # fallback: última seção
        if len(depois) > len(antes):
            novas = depois[len(antes):]
        else:
            _ativar_modo_edicao(session, course_id, ligar=False, dry_run=False)
            return {
                "sucesso": False,
                "dry_run": False,
                "acao": "criar_secao",
                "nome": nome,
                "posicao": insert_at,
                "mensagem": "Seção criada não foi localizada após changenumsections.",
            }

    nova = novas[-1]
    ren = atualizar_secao(session, nova["section_id"], nome=nome, dry_run=False)
    _ativar_modo_edicao(session, course_id, ligar=False, dry_run=False)
    return {
        "sucesso": bool(ren.get("sucesso")),
        "dry_run": False,
        "acao": "criar_secao",
        "nome": nome,
        "posicao": insert_at,
        "section_id": nova["section_id"],
        "mensagem": ren.get("mensagem"),
    }


def atualizar_secao(
    session: Session,
    section_id: str,
    *,
    nome: str | None = None,
    visivel: bool | None = None,
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
            "sucesso": False,
            "dry_run": dry_run,
            "acao": "atualizar_secao",
            "section_id": section_id,
            "mensagem": str(exc),
        }

    if nome is not None:
        data["name"] = nome
    # visibilidade: campo nem sempre presente; ignora se ausente
    if visivel is not None and "visible" in data:
        data["visible"] = "1" if visivel else "0"

    data["submitbutton"] = "Salvar alterações"
    action = form.get("action") or f"{MOODLE_BASE}/course/editsection.php"
    if action.startswith("/"):
        action = MOODLE_BASE + action

    if dry_run:
        return {
            "sucesso": True,
            "dry_run": True,
            "acao": "atualizar_secao",
            "section_id": section_id,
            "nome": nome,
            "payload_campos": len(data),
            "mensagem": f"Simularía renomear section_id={section_id} para '{nome}'.",
        }

    post = session.post(action, data=data, allow_redirects=True)
    ok = post.status_code == 200
    return {
        "sucesso": ok,
        "dry_run": False,
        "acao": "atualizar_secao",
        "section_id": section_id,
        "nome": nome,
        "status_code": post.status_code,
        "mensagem": None if ok else f"HTTP {post.status_code}",
    }


def criar_atividade(
    session: Session,
    course_id: str,
    section_num: int,
    tipo: str,
    nome: str,
    *,
    intro: str | None = None,
    opcoes: dict | None = None,
    dry_run: bool = True,
) -> dict:
    """Cria uma atividade Moodle na seção indicada.

    Tipos suportados: ``url``, ``folder``, ``hsuforum``, ``assign``, ``quiz``.
    LTI não é suportado. ``dry_run=True`` por padrão.

    Args:
        section_num: índice da seção (0 = primeira), não o section_id.
        opcoes: extras (ex. ``{"externalurl": "https://..."}`` para url).
    """
    tipo = (tipo or "").lower().strip()
    if tipo not in _TIPOS_ATIVIDADE:
        return {
            "sucesso": False,
            "dry_run": dry_run,
            "acao": "criar_atividade",
            "tipo": tipo,
            "nome": nome,
            "mensagem": f"Tipo '{tipo}' não suportado. Use: {_TIPOS_ATIVIDADE}",
        }

    opcoes = opcoes or {}
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
            "sucesso": False,
            "dry_run": dry_run,
            "acao": "criar_atividade",
            "tipo": tipo,
            "nome": nome,
            "mensagem": str(exc),
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
        url = opcoes.get("externalurl") or opcoes.get("url") or "https://on.unoesc.edu.br"
        data["externalurl"] = url

    for k, v in opcoes.items():
        if k in ("externalurl", "url"):
            continue
        data[k] = str(v)

    # Salvar e voltar ao curso
    data["submitbutton2"] = "Salvar e voltar ao curso"
    data.pop("submitbutton", None)

    action = form.get("action") or f"{MOODLE_BASE}/course/modedit.php"
    if action.startswith("/"):
        action = MOODLE_BASE + action
    if not action.startswith("http"):
        action = f"{MOODLE_BASE}/course/{action}"

    if dry_run:
        return {
            "sucesso": True,
            "dry_run": True,
            "acao": "criar_atividade",
            "tipo": tipo,
            "nome": nome,
            "section_num": section_num,
            "payload_campos": len(data),
            "mensagem": f"Simularía criar {tipo} '{nome}' na seção {section_num}.",
        }

    post = session.post(action, data=data, allow_redirects=True)
    # tenta extrair cmid da URL final
    m = re.search(r"[?&]id=(\d+)", post.url or "")
    activity_id = m.group(1) if m and "mod/" in (post.url or "") else None
    ok = post.status_code == 200
    return {
        "sucesso": ok,
        "dry_run": False,
        "acao": "criar_atividade",
        "tipo": tipo,
        "nome": nome,
        "section_num": section_num,
        "activity_id": activity_id,
        "status_code": post.status_code,
        "url": post.url,
        "mensagem": None if ok else f"HTTP {post.status_code}",
    }


# ── Tarefas (assign) ──────────────────────────────────────────────────────────

def ver_tarefa(session: Session, activity_id: str) -> dict:
    """Retorna detalhes de uma tarefa (assign).

    Returns:
        dict: {titulo, descricao, prazo, url}
    """
    resp = session.get(f"{MOODLE_BASE}/mod/assign/view.php?id={activity_id}")
    soup = _soup(resp.text)
    titulo   = soup.find("h2")
    descricao = soup.find("div", class_=re.compile("description|intro"))
    prazo    = soup.find(string=re.compile(r"prazo|due|entrega", re.I))
    return {
        "titulo":    titulo.get_text(strip=True) if titulo else "",
        "descricao": descricao.get_text(strip=True)[:500] if descricao else "",
        "prazo":     prazo.strip() if prazo else "",
        "url":       resp.url,
    }


# ── Questionários (quiz) ──────────────────────────────────────────────────────

def ver_quiz(session: Session, activity_id: str) -> dict:
    """Retorna detalhes de um questionário (quiz).

    Returns:
        dict: {titulo, intro, url}
    """
    resp = session.get(f"{MOODLE_BASE}/mod/quiz/view.php?id={activity_id}")
    soup = _soup(resp.text)
    titulo = soup.find("h2") or soup.find("h1")
    intro  = soup.find("div", class_=re.compile("intro|description"))
    return {
        "titulo": titulo.get_text(strip=True) if titulo else "",
        "intro":  intro.get_text(strip=True)[:500] if intro else "",
        "url":    resp.url,
    }


# ── Fóruns (hsuforum) ─────────────────────────────────────────────────────────

def ver_forum(session: Session, activity_id: str) -> dict:
    """Retorna posts de um fórum.

    Returns:
        dict: {titulo, posts: [{autor, corpo}, ...], url}
    """
    resp = session.get(f"{MOODLE_BASE}/mod/hsuforum/view.php?id={activity_id}")
    soup = _soup(resp.text)
    titulo = soup.find("h2") or soup.find("h1")
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
        "titulo": titulo.get_text(strip=True) if titulo else "",
        "posts":  resultado,
        "url":    resp.url,
    }


# ── Recursos (resource / url) ─────────────────────────────────────────────────

def baixar_recurso(session: Session, activity_id: str, destino: str | None = None) -> str:
    """Baixa um arquivo de recurso (tipo 'resource').

    Args:
        activity_id: ID da atividade do tipo resource.
        destino: caminho completo para salvar. None = ~/Downloads/<nome_original>.

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
    if destino is None:
        destino = os.path.expanduser(f"~/Downloads/{nome}")
    with open(destino, "wb") as f:
        f.write(resp.content)
    print(f"Arquivo salvo em: {destino}")
    return destino
