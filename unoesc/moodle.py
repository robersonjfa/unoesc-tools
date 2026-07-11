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
