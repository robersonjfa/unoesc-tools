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
    """Lista diários de classe disponíveis para preenchimento.

    Returns:
        list[dict] com colunas: Componente curricular, Fase, Turma,
        Estudantes, Pessoas com Deficiência (PcD).
    """
    params = {"selAnoPeriodo": ano_periodo} if ano_periodo else None
    resp = _get(session, "diario_classe", params)
    return _tabela(_soup(resp.text))


def abrir_diario(session: Session, cod_disciplina_ofertada: str) -> str:
    """Retorna HTML bruto do diário de classe de uma disciplina.

    Args:
        cod_disciplina_ofertada: código numérico da disciplina ofertada.
    """
    resp = session.get(
        f"{BASE_URL}/portal/modules/prof/diarioClasse.jspa",
        params={"codDisciplinaOfertada": cod_disciplina_ofertada},
    )
    return resp.text


# ── Plano de Ensino ───────────────────────────────────────────────────────────

def listar_planos_ensino(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Lista planos de ensino disponíveis para preenchimento.

    Returns:
        list[dict] com as disciplinas e status do plano.
    """
    params = {"selAnoPeriodo": ano_periodo} if ano_periodo else None
    resp = _get(session, "plano_ensino", params)
    return _tabela(_soup(resp.text))


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

def listar_alunos_para_mensagem(session: Session, ano_periodo: str | None = None) -> list[dict]:
    """Lista alunos disponíveis para receber mensagem direta.

    Returns:
        list[dict] com nome, RA e e-mail.
    """
    params = {"selAnoPeriodo": ano_periodo} if ano_periodo else None
    resp = _get(session, "mensagem_alunos", params)
    return _tabela(_soup(resp.text))


def enviar_mensagem_alunos(session: Session, alunos: str | list[str], assunto: str, mensagem: str, origem: str = "") -> bool:
    """Envia mensagem acadêmica direta para alunos.

    Args:
        alunos:   RA (str) ou lista de RAs.
        assunto:  assunto da mensagem.
        mensagem: corpo da mensagem.
        origem:   campo de origem opcional.

    Returns:
        True se enviado com sucesso.
    """
    data = {
        "origem":     origem,
        "assunto":    assunto,
        "mensagem":   mensagem,
        "sel_alunos": alunos if isinstance(alunos, list) else [alunos],
        "compor":     "1",
    }
    resp = _post(session, "mensagem_alunos", data)
    return resp.status_code == 200


def enviar_notificacao_on(session: Session, mensagem: str, disciplinas: str | list[str]) -> bool:
    """Envia notificação push via app Unoesc ON.

    Args:
        mensagem:    texto da notificação.
        disciplinas: código DOF (str) ou lista de DOFs das disciplinas.

    Returns:
        True se enviado com sucesso.
    """
    data = {
        "mensagem":        mensagem,
        "disclecionada[]": disciplinas if isinstance(disciplinas, list) else [disciplinas],
    }
    resp = _post(session, "notificacao_on", data)
    return resp.status_code == 200


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
