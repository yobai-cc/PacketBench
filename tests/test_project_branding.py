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
