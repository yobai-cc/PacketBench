from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_deployment_files_use_packetbench_name() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    service_file = (ROOT / "systemd" / "app.service").read_text(encoding="utf-8")

    assert "# PacketBench" in readme
    assert "当前版本：`v0.1.0`" in readme
    assert "/opt/packetbench" in readme
    assert "packetbench.service" in readme
    assert "Description=PacketBench" in service_file
    assert "/opt/packetbench" in service_file
    assert "u2t-web.service" not in readme
    assert "u2t_web" not in readme


def test_ubuntu_adaptation_doc_covers_public_ip_ports_and_caddy() -> None:
    adaptation_doc = (ROOT / "docs" / "2026-04-09-ubuntu-deployment-adaptation.md").read_text(encoding="utf-8")
    caddy_example = (ROOT / "Caddyfile.example").read_text(encoding="utf-8")

    assert "curl -4 ifconfig.me" in adaptation_doc
    assert "127.0.0.1:8080" in adaptation_doc
    assert "9000/udp" in adaptation_doc
    assert "9100/tcp" in adaptation_doc
    assert "reverse_proxy 127.0.0.1:8080" in adaptation_doc
    assert "packetbench.example.com" in caddy_example
