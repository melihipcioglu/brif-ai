"""Unit and integration tests for BRIF.AI Demo Launcher."""

from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from brif_ai.demo.launcher import (
    DemoProcessManager,
    check_model_available,
    check_ollama_service,
    check_port_free,
    check_project_root,
    check_required_modules,
    check_virtual_environment,
    run_all_preflight_checks,
    wait_for_api_ready,
    wait_for_ui_ready,
)


def test_check_project_root_valid(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")
    ui_dir = tmp_path / "prototypes" / "conversation_ui_v0"
    ui_dir.mkdir(parents=True)
    (ui_dir / "index.html").write_text("<html></html>")

    ok, msg = check_project_root(tmp_path)
    assert ok is True
    assert "doğrulandı" in msg.lower()


def test_check_project_root_invalid(tmp_path: Path) -> None:
    ok, msg = check_project_root(tmp_path)
    assert ok is False
    assert "geçersiz proje dizini" in msg.lower()


def test_check_virtual_environment_valid(tmp_path: Path) -> None:
    scripts_dir = tmp_path / ".venv" / "Scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "python.exe").write_text("")

    ok, msg = check_virtual_environment(tmp_path)
    assert ok is True
    assert "sanal ortam" in msg.lower()


def test_check_virtual_environment_invalid(tmp_path: Path) -> None:
    ok, msg = check_virtual_environment(tmp_path / "empty_dir")
    assert ok is False
    assert "bulunamadı" in msg.lower()


def test_check_required_modules() -> None:
    ok, msg = check_required_modules()
    assert ok is True
    assert "gerekli python modülleri" in msg.lower()


def test_check_port_free_valid() -> None:
    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = int(s.getsockname()[1])

    ok, msg = check_port_free(free_port)
    assert ok is True
    assert "boş" in msg.lower()


def test_check_port_free_zero_rejected() -> None:
    """Verify port 0 is strictly rejected."""
    ok, msg = check_port_free(0)
    assert ok is False
    assert "geçersiz port numarası" in msg.lower()


def test_check_port_free_busy() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        busy_port = int(s.getsockname()[1])

        ok_busy, msg_busy = check_port_free(busy_port)
        assert ok_busy is False
        assert "kullanılıyor" in msg_busy.lower()


def test_preflight_checks_rejects_same_api_and_ui_ports(tmp_path: Path) -> None:
    """Verify preflight check fails immediately if API and UI ports collide."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")
    ui_dir = tmp_path / "prototypes" / "conversation_ui_v0"
    ui_dir.mkdir(parents=True)
    (ui_dir / "index.html").write_text("<html></html>")
    (tmp_path / ".venv" / "Scripts").mkdir(parents=True)
    (tmp_path / ".venv" / "Scripts" / "python.exe").write_text("")

    results = run_all_preflight_checks(
        project_root=tmp_path,
        api_port=8080,
        ui_port=8080,
        check_ollama=False,
    )
    failed = [msg for ok, msg in results if not ok]
    assert any("aynı olamaz" in msg for msg in failed)


def test_check_ollama_service_reachable() -> None:
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        ok, msg = check_ollama_service("http://127.0.0.1:11434")
        assert ok is True
        assert "erişilebilir" in msg.lower()


def test_check_ollama_service_unreachable() -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
        ok, msg = check_ollama_service("http://127.0.0.1:11434")
        assert ok is False
        assert "ulaşılamıyor" in msg.lower()


def test_check_model_available_present() -> None:
    json_bytes = b'{"models": [{"name": "qwen3:4b-instruct"}, {"name": "llama3:latest"}]}'
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.read.return_value = json_bytes
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        ok, msg = check_model_available("qwen3:4b-instruct", "http://127.0.0.1:11434")
        assert ok is True
        assert "mevcut" in msg.lower()


def test_check_model_available_missing() -> None:
    json_bytes = b'{"models": [{"name": "llama3:latest"}]}'
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.read.return_value = json_bytes
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        ok, msg = check_model_available("qwen3:4b-instruct", "http://127.0.0.1:11434")
        assert ok is False
        assert "yüklü değil" in msg.lower()


def test_check_model_available_rejects_different_tag_only() -> None:
    """Verify qwen3:8b does NOT satisfy requirement for qwen3:4b-instruct."""
    json_bytes = b'{"models": [{"name": "qwen3:8b"}, {"model": "qwen3:72b"}]}'
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.read.return_value = json_bytes
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        ok, msg = check_model_available("qwen3:4b-instruct", "http://127.0.0.1:11434")
        assert ok is False
        assert "yüklü değil" in msg.lower()


def test_check_model_available_accepts_exact_target() -> None:
    """Verify qwen3:4b-instruct:latest or qwen3:4b-instruct matches exactly."""
    json_bytes = b'{"models": [{"name": "qwen3:4b-instruct:latest"}]}'
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.read.return_value = json_bytes
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        ok, msg = check_model_available("qwen3:4b-instruct", "http://127.0.0.1:11434")
        assert ok is True
        assert "mevcut" in msg.lower()


def test_wait_for_api_ready_success() -> None:
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        ready = wait_for_api_ready("http://127.0.0.1:8000", timeout=1.0)
        assert ready is True


def test_wait_for_ui_ready_success() -> None:
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        ready = wait_for_ui_ready("http://127.0.0.1:8080", timeout=1.0)
        assert ready is True


def test_demo_process_manager_only_stops_owned_processes() -> None:
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None

    manager = DemoProcessManager()
    manager.register_process("api", mock_proc)

    manager.stop_all()
    mock_proc.terminate.assert_called_once()


@pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows PowerShell environment")
def test_powershell_script_missing_venv_exits_with_turkish_error(tmp_path: Path) -> None:
    """Verify PowerShell script exits cleanly with exit code 1 if .venv is missing."""
    dummy_ps1 = tmp_path / "run_demo.ps1"
    real_ps1 = Path("run_demo.ps1").read_text(encoding="utf-8")
    dummy_ps1.write_text(real_ps1, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'", encoding="utf-8")

    cmd = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(dummy_ps1),
    ]
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(tmp_path),
    )

    stdout = res.stdout or ""
    stderr = res.stderr or ""
    output = stdout + stderr

    assert res.returncode == 1
    assert "sanal ortam" in output and "bulunamad" in output
    assert "Traceback" not in output
    assert "ModuleNotFoundError" not in output


@pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows PowerShell environment")
def test_powershell_script_from_outside_working_directory(tmp_path: Path) -> None:
    """Verify PowerShell script invoked from a different directory resolves project root."""
    real_root = Path(".").resolve()
    script_path = real_root / "run_demo.ps1"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy_s:
        busy_s.bind(("127.0.0.1", 0))
        busy_s.listen(1)
        busy_port = int(busy_s.getsockname()[1])

        cmd = [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-NoBrowser",
            "-NoOllamaCheck",
            "-ApiPort",
            str(busy_port),
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(tmp_path),
        )

        output = (res.stdout or "") + (res.stderr or "")
        assert "Proje dizini" in output or "Kontroller" in output or "kullanılıyor" in output
