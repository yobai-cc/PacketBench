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


def test_maintenance_guide_is_linked_from_docs_index_and_readme() -> None:
    maintenance_guide = (ROOT / "docs" / "ai-maintenance-guide.md").read_text(encoding="utf-8")
    docs_index = (ROOT / "docs" / "INDEX.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "# AI Maintenance Guide" in maintenance_guide
    assert "release/ubuntu-v0.1.0" in maintenance_guide
    assert "docs/ai-maintenance-guide.md" in readme
    assert "ai-maintenance-guide.md" in docs_index
