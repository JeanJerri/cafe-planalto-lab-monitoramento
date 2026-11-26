"""Testes automatizados para validar configurações de observabilidade da Fase 2."""

from pathlib import Path
import re

INTEGRANTE_B_DIR = Path(__file__).resolve().parents[2]
OBS_DIR = INTEGRANTE_B_DIR / "observability"

REQUIRED_JOBS = (
    "prometheus",
    "api",
    "nginx_exporter",
    "postgres_exporter",
    "node_exporter",
    "cadvisor",
    "blackbox_exporter",
    "blackbox_http",
    "blackbox_dns",
    "blackbox_icmp",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_arquivos_observabilidade_sem_crlf():
    arquivos = [
        OBS_DIR / "blackbox" / "blackbox.yml",
        OBS_DIR / "prometheus" / "prometheus.local.yml",
        OBS_DIR / "prometheus" / "prometheus.clab.yml",
        OBS_DIR / "prometheus" / "rules" / "alerts.yml",
        OBS_DIR / "alertmanager" / "alertmanager.yml.tmpl",
        OBS_DIR / "alertmanager" / "entrypoint.sh",
        OBS_DIR / "dns-dev" / "Corefile",
        INTEGRANTE_B_DIR / "docker-compose.yml",
    ]
    for arquivo in arquivos:
        raw = arquivo.read_bytes()
        assert b"\r" not in raw, f"Encontrado CR (CRLF) em {arquivo}"


def test_blackbox_possui_modulos_http_dns_icmp():
    conteudo = _read_text(OBS_DIR / "blackbox" / "blackbox.yml")
    assert "http_2xx:" in conteudo
    assert "prober: http" in conteudo
    assert "dns_cafeplanalto:" in conteudo
    assert "prober: dns" in conteudo
    assert 'query_name: "loja.cafeplanalto.lab"' in conteudo
    assert "icmp:" in conteudo
    assert "prober: icmp" in conteudo


def test_prometheus_local_e_clab_possuem_todos_os_jobs_e_regra_de_ouro():
    local_cfg = _read_text(OBS_DIR / "prometheus" / "prometheus.local.yml")
    clab_cfg = _read_text(OBS_DIR / "prometheus" / "prometheus.clab.yml")

    for cfg in (local_cfg, clab_cfg):
        assert "/etc/prometheus/rules/alerts.yml" in cfg
        for job in REQUIRED_JOBS:
            assert f'job_name: "{job}"' in cfg, f"Job {job} ausente"

    # Regra de Ouro: Containerlab jamais pode coletar pela rede fora de banda eth0 (172.30.0.0/24)
    clab_sem_comentarios = "\n".join(
        line for line in clab_cfg.splitlines() if not line.lstrip().startswith("#")
    )
    assert "172.30.0." not in clab_sem_comentarios
    assert "172.20.20.30:9115" in clab_cfg
    assert "172.20.10.10:53" in clab_cfg
    assert "172.20.99.21:9093" in clab_cfg
    assert "10.0.0.1" in clab_cfg
    assert "10.0.0.2" in clab_cfg


def test_regras_de_alerta_tem_for_severity_e_cobrem_falhas():
    rules = _read_text(OBS_DIR / "prometheus" / "rules" / "alerts.yml")
    alert_blocks = re.split(r"\n\s*- alert:\s+", "\n" + rules)[1:]
    assert len(alert_blocks) == 10

    nomes_esperados = {
        "EnlaceWANOuSondaIndisponivel",
        "AlvoPrometheusFora",
        "LojaIndisponivelHTTP",
        "DNSInternoFalhando",
        "FalhaICMPDestino",
        "LatenciaAltaSondaHTTP",
        "BancoPostgreSQLFora",
        "TaxaDeErros5xxAlta",
        "LatenciaP95AcimaDoSLO",
        "MemoriaAltaHost",
    }
    nomes_encontrados = set()

    for block in alert_blocks:
        nome = block.splitlines()[0].strip()
        nomes_encontrados.add(nome)
        for campo in ("expr:", "for:", "severity:", "servico:", "tipo:", "summary:", "description:"):
            assert campo in block, f"Campo obrigatório {campo} ausente no alerta {nome}"

    assert nomes_encontrados == nomes_esperados


def test_alertmanager_email_agrupamento_inhibit_e_env_example():
    tmpl = _read_text(OBS_DIR / "alertmanager" / "alertmanager.yml.tmpl")
    entrypoint = _read_text(OBS_DIR / "alertmanager" / "entrypoint.sh")
    env_example = _read_text(INTEGRANTE_B_DIR / ".env.example")

    assert "email_configs:" in tmpl
    assert "send_resolved: true" in tmpl
    assert "group_by:" in tmpl
    assert "group_wait:" in tmpl
    assert "inhibit_rules:" in tmpl
    assert "${SMTP_AUTH_PASSWORD}" in tmpl
    assert "${ALERT_EMAIL_TO}" in tmpl

    # Garante que envsubst preserva templates Go {{ ... }} usando lista explícita
    assert "envsubst '${SMTP_SMARTHOST}" in entrypoint

    for var in (
        "SMTP_SMARTHOST=",
        "SMTP_FROM=",
        "SMTP_AUTH_USERNAME=",
        "SMTP_AUTH_PASSWORD=",
        "SMTP_REQUIRE_TLS=",
        "ALERT_EMAIL_TO=",
        "CADVISOR_HOST_PORT=",
    ):
        assert var in env_example, f"Variável {var} ausente no .env.example"


def test_dockerfiles_sem_crlf_e_sem_cmd_multilinha_invalido():
    dockerfiles = list(INTEGRANTE_B_DIR.rglob("Dockerfile*"))
    assert dockerfiles
    for df in dockerfiles:
        raw = df.read_bytes()
        assert b"\r" not in raw, f"Encontrado CR (CRLF) em {df}"
        text = raw.decode("utf-8")
        assert not re.search(r"(?m)^(CMD|ENTRYPOINT)\s+\[\s*\n", text), (
            f"CMD/ENTRYPOINT multilinha sem barra invertida em {df}"
        )
