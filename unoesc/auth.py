"""
Autenticação e gerenciamento de sessão para o Portal UNOESC.

Ordem de resolução das credenciais:
  1. Variáveis de ambiente: UNOESC_USUARIO e UNOESC_SENHA  (headless / CI / Codex)
  2. Config file ~/.unoesc_config.json + dialog macOS       (uso interativo)

Cookies de sessão são salvos em ~/.unoesc_session.json (permissão 600).
A senha nunca é persistida em disco.
"""
import json
import os
import subprocess
import sys
import requests
from requests import Session

BASE_URL     = "https://acad.unoesc.edu.br/academico"
SESSION_FILE = os.path.expanduser("~/.unoesc_session.json")
CONFIG_FILE  = os.path.expanduser("~/.unoesc_config.json")


def _dialog(message, title="UNOESC", oculto=False):
    """Dialog nativo macOS. Não disponível em ambientes headless."""
    hidden = "with hidden answer" if oculto else ""
    script = (
        f'display dialog "{message}" default answer "" {hidden} '
        f'with title "{title}" buttons {{"Cancelar", "OK"}} default button "OK"'
    )
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        print("Cancelado.")
        sys.exit(0)
    return result.stdout.strip().split("text returned:")[-1]


def _load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def _save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
    os.chmod(CONFIG_FILE, 0o600)


def _get_username():
    # 1. variável de ambiente
    if os.environ.get("UNOESC_USUARIO"):
        return os.environ["UNOESC_USUARIO"]
    # 2. config file
    config = _load_config()
    if "usuario" not in config:
        if sys.platform != "darwin":
            raise RuntimeError(
                "Defina a variável de ambiente UNOESC_USUARIO com seu código/CPF."
            )
        usuario = _dialog("Código ou CPF UNOESC:", title="UNOESC - Identificação")
        config["usuario"] = usuario.strip()
        _save_config(config)
        print(f"Código salvo: {config['usuario']}")
    return config["usuario"]


def _get_password():
    # 1. variável de ambiente
    if os.environ.get("UNOESC_SENHA"):
        return os.environ["UNOESC_SENHA"]
    # 2. dialog macOS
    if sys.platform != "darwin":
        raise RuntimeError(
            "Defina a variável de ambiente UNOESC_SENHA com sua senha."
        )
    return _dialog("Senha UNOESC:", title="UNOESC - Login", oculto=True)


def _save_session(cookies):
    with open(SESSION_FILE, "w") as f:
        json.dump(cookies, f)
    os.chmod(SESSION_FILE, 0o600)


def _load_session():
    if not os.path.exists(SESSION_FILE):
        return None
    with open(SESSION_FILE) as f:
        return json.load(f)


def new_session(cookies: dict | None = None) -> Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
    if cookies:
        requests.utils.add_dict_to_cookiejar(s.cookies, cookies)
    return s


def _session_valid(session):
    try:
        resp = session.get(
            f"{BASE_URL}/portal/modules/prof/aulaOnlineMoodlerooms.jspa?t=1",
            allow_redirects=False,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _do_login():
    usuario = _get_username()
    senha   = _get_password()
    s = new_session()
    s.get(BASE_URL)
    resp = s.post(
        f"{BASE_URL}/j_security_check",
        data={"j_username": usuario, "j_password": senha, "acessar": "Entrar"},
        allow_redirects=True,
    )
    if "j_security_check" in resp.url or "login" in resp.url.lower():
        # Em modo interativo, limpa o usuário salvo e tenta de novo
        if not os.environ.get("UNOESC_USUARIO"):
            config = _load_config()
            config.pop("usuario", None)
            _save_config(config)
        if sys.platform == "darwin" and not os.environ.get("UNOESC_SENHA"):
            print("Credenciais incorretas. Tente novamente.")
            return _do_login()
        raise RuntimeError("Login falhou. Verifique UNOESC_USUARIO e UNOESC_SENHA.")
    _save_session(requests.utils.dict_from_cookiejar(s.cookies))
    print("Login realizado com success.")
    return s


def open_session() -> Session:
    """Retorna uma sessão HTTP autenticada no Portal UNOESC.

    Reutiliza cookies salvos enquanto a sessão for válida.
    Solicita código/CPF (uma vez) e senha (a cada expiração) via dialog macOS.
    Em ambiente headless, lê UNOESC_USUARIO e UNOESC_SENHA das variáveis de ambiente.

    Returns:
        requests.Session autenticada, válida para portal e Moodle.
    """
    cookies = _load_session()
    if cookies:
        s = new_session(cookies)
        if _session_valid(s):
            print("Sessão ativa reutilizada.")
            return s
    print("Sessão expirada. Fazendo login...")
    return _do_login()
