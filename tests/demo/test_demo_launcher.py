"""Unit and integration tests for BRIF.AI Demo Launcher."""

from __future__ import annotations

import socket
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from brif_ai.demo.launcher import (
    DemoProcessManager,
    check_model_available,
    check_ollama_service,
    check_port_free,
    check_project_root,
    check_required_modules,
    check_virtual_environment,
    wait_for_api_ready,
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


def test_check_port_free() -> None:
    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = int(s.getsockname()[1])

    ok, msg = check_port_free(free_port)
    assert ok is True
    assert "boş" in msg.lower()

    # Test busy port
    s_busy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_busy.bind(("127.0.0.1", free_port))
    s_busy.listen(1)

    try:
        ok_busy, msg_busy = check_port_free(free_port)
        assert ok_busy is False
        assert "kullanılıyor" in msg_busy.lower()
    finally:
        s_busy.close()


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


def test_wait_for_api_ready_success() -> None:
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        ready = wait_for_api_ready("http://127.0.0.1:8000", timeout=1.0)
        assert ready is True


def test_wait_for_api_ready_timeout() -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
        start = time.time()
        ready = wait_for_api_ready("http://127.0.0.1:8000", timeout=0.5)
        elapsed = time.time() - start
        assert ready is False
        assert elapsed >= 0.4


def test_demo_process_manager_only_stops_owned_processes() -> None:
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None

    manager = DemoProcessManager()
    manager.register_process("api", mock_proc)

    manager.stop_all()
    mock_proc.terminate.assert_called_once()
