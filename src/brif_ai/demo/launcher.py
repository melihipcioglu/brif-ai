"""BRIF.AI Local Demo Launcher and Preflight Check Engine."""

from __future__ import annotations

import argparse
import atexit
import contextlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


def check_project_root(project_root: Path | str = ".") -> tuple[bool, str]:
    """Verify current path contains BRIF.AI project root markers."""
    root = Path(project_root).resolve()
    pyproject = root / "pyproject.toml"
    ui_index = root / "prototypes" / "conversation_ui_v0" / "index.html"

    if pyproject.is_file() and ui_index.is_file():
        return True, f"Proje dizini doğrulandı: {root}"
    return (
        False,
        "Hata: Geçersiz proje dizini. Lütfen komutu BRIF.AI proje kök dizininde çalıştırın.",
    )


def check_virtual_environment(project_root: Path | str = ".") -> tuple[bool, str]:
    """Verify Python virtual environment (.venv) exists."""
    root = Path(project_root).resolve()
    venv_python_win = root / ".venv" / "Scripts" / "python.exe"
    venv_python_nix = root / ".venv" / "bin" / "python"

    if venv_python_win.is_file() or venv_python_nix.is_file():
        return True, "Python sanal ortamı (.venv) doğrulandı."

    # Fallback to current sys.prefix if project_root is default current working directory
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    if root == Path(".").resolve() and in_venv:
        return True, "Python sanal ortamı (.venv) doğrulandı."

    return (
        False,
        "Hata: Python sanal ortamı (.venv) bulunamadı. Lütfen sanal ortamı hazırlayın.",
    )


def check_required_modules() -> tuple[bool, str]:
    """Verify required Python packages are importable."""
    missing: list[str] = []
    for module_name in ["fastapi", "uvicorn", "brif_ai"]:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)

    if not missing:
        return True, "Gerekli Python modülleri doğrulandı."
    return (
        False,
        f"Hata: Gerekli Python modülleri ({', '.join(missing)}) sanal ortamda bulunamadı.",
    )


def check_ollama_service(ollama_url: str = "http://127.0.0.1:11434") -> tuple[bool, str]:
    """Verify Ollama local service is reachable."""
    endpoint = f"{ollama_url.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(endpoint, method="GET")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                return True, f"Ollama servisi erişilebilir ({ollama_url})."
    except Exception:
        pass
    return (
        False,
        f"Hata: Ollama servisine ({ollama_url}) ulaşılamıyor. "
        "Lütfen Ollama uygulamasının arka planda çalıştığından emin olun.",
    )


def check_model_available(
    model_name: str = "qwen3:4b-instruct",
    ollama_url: str = "http://127.0.0.1:11434",
) -> tuple[bool, str]:
    """Verify configured model is installed in Ollama with exact match."""
    endpoint = f"{ollama_url.rstrip('/')}/api/tags"
    target = model_name.strip().lower()

    try:
        req = urllib.request.Request(endpoint, method="GET")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                installed_models: set[str] = set()

                for m in data.get("models", []):
                    if isinstance(m, dict):
                        for key in ("name", "model"):
                            val = m.get(key)
                            if isinstance(val, str) and val.strip():
                                name_lower = val.strip().lower()
                                installed_models.add(name_lower)
                                if name_lower.endswith(":latest"):
                                    installed_models.add(name_lower[:-7])

                target_latest = f"{target}:latest" if ":" not in target else target
                target_base = target[:-7] if target.endswith(":latest") else target

                is_available = (
                    target in installed_models
                    or target_latest in installed_models
                    or target_base in installed_models
                )

                if is_available:
                    return True, f"Model '{model_name}' Ollama servisinde mevcut."
    except Exception:
        pass

    return (
        False,
        f"Hata: Belirtilen yerel model ('{model_name}') Ollama servisinde yüklü değil. "
        f"Lütfen modeli indirin: ollama run {model_name}",
    )


def check_port_free(port: int, host: str = "127.0.0.1") -> tuple[bool, str]:
    """Verify port is valid (1-65535) and free on local machine."""
    if not (1 <= port <= 65535):
        return (
            False,
            f"Hata: Geçersiz port numarası ({port}). Port 1 ile 65535 arasında olmalıdır.",
        )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True, f"Port {port} boş."
        except OSError:
            return (
                False,
                f"Hata: Port {port} başka bir süreç tarafından kullanılıyor. "
                "Lütfen çakışan süreci kapatın veya farklı bir port belirtin.",
            )


def run_all_preflight_checks(
    project_root: Path | str = ".",
    api_port: int = 8000,
    ui_port: int = 8080,
    model_name: str = "qwen3:4b-instruct",
    ollama_url: str = "http://127.0.0.1:11434",
    check_ollama: bool = True,
) -> list[tuple[bool, str]]:
    """Run all preflight checks sequentially."""
    root = Path(project_root).resolve()
    checks: list[tuple[bool, str]] = []

    checks.append(check_project_root(root))
    checks.append(check_virtual_environment(root))
    checks.append(check_required_modules())

    if api_port == ui_port:
        checks.append(
            (
                False,
                f"Hata: API portu ve Arayüz portu aynı olamaz ({api_port}). "
                "Lütfen farklı portlar belirtin.",
            )
        )
    else:
        checks.append(check_port_free(api_port))
        checks.append(check_port_free(ui_port))

    if check_ollama:
        ollama_ok, ollama_msg = check_ollama_service(ollama_url)
        checks.append((ollama_ok, ollama_msg))
        if ollama_ok:
            checks.append(check_model_available(model_name, ollama_url))

    return checks


def wait_for_api_ready(
    api_url: str,
    timeout: float = 15.0,
    expected_model: str = "qwen3:4b-instruct",
    expected_provider: str = "ollama",
) -> tuple[bool, str]:
    """Poll API health endpoint until ready with real LLM verification or timeout expires."""
    endpoint = f"{api_url.rstrip('/')}/api/v1/health"
    start_time = time.time()
    last_error = "API servisine ulaşılamadı."

    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(endpoint, method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    status = str(data.get("status", ""))
                    llm_enabled = bool(data.get("llm_enabled", False))
                    provider = str(data.get("provider", ""))
                    provider_reachable = bool(data.get("provider_reachable", False))
                    selected_model = data.get("selected_model")
                    model_available = bool(data.get("model_available", False))

                    if status != "ok":
                        last_error = f"Hata: API sağlık durumu uygun değil (status='{status}')."
                        time.sleep(0.3)
                        continue

                    if not llm_enabled:
                        last_error = (
                            "Hata: API LLM bağlantısı etkinleştirilmedi (llm_enabled=false)."
                        )
                        time.sleep(0.3)
                        continue

                    if provider != expected_provider or not provider_reachable:
                        last_error = (
                            f"Hata: Sağlayıcı '{expected_provider}' erişilebilir değil "
                            f"(provider='{provider}', reachable={provider_reachable})."
                        )
                        time.sleep(0.3)
                        continue

                    if selected_model != expected_model:
                        last_error = (
                            f"Hata: Seçilen model eşleşmiyor (Beklenen: '{expected_model}', "
                            f"API: '{selected_model}')."
                        )
                        time.sleep(0.3)
                        continue

                    if not model_available:
                        last_error = (
                            f"Hata: Seçilen model '{expected_model}' API tarafında "
                            "kullanılabilir görünmüyor (model_available=false)."
                        )
                        time.sleep(0.3)
                        continue

                    return True, "API servisi ve yerel LLM bağlantısı hazır."
        except Exception as exc:
            last_error = f"API sağlık kontrolü hatası: {exc}"
            time.sleep(0.3)

    return False, last_error


def wait_for_ui_ready(ui_url: str, timeout: float = 15.0) -> bool:
    """Poll UI HTTP endpoint until ready or timeout expires."""
    endpoint = f"{ui_url.rstrip('/')}/index.html"
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(endpoint, method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


class DemoProcessManager:
    """Manages owned child processes for the BRIF.AI demo."""

    def __init__(self) -> None:
        self.processes: dict[str, subprocess.Popen[bytes]] = {}

    def register_process(self, name: str, proc: subprocess.Popen[bytes]) -> None:
        self.processes[name] = proc

    def stop_all(self) -> None:
        """Safely terminate only child processes spawned by this manager."""
        for _name, proc in list(self.processes.items()):
            if proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=2.0)
                except (subprocess.TimeoutExpired, OSError):
                    try:
                        proc.kill()
                        proc.wait()
                    except OSError:
                        pass
        self.processes.clear()


DEFAULT_DEMO_LLM_TIMEOUT_SECONDS: float = 300.0
DEFAULT_DEMO_NUM_PREDICT: int = 512


def launch_demo(
    project_root: Path | str = ".",
    api_port: int = 8000,
    ui_port: int = 8080,
    model_name: str = "qwen3:4b-instruct",
    ollama_url: str = "http://127.0.0.1:11434",
    open_browser: bool = True,
    check_ollama: bool = True,
    llm_timeout: float = DEFAULT_DEMO_LLM_TIMEOUT_SECONDS,
    num_predict: int = DEFAULT_DEMO_NUM_PREDICT,
) -> None:
    """Run checks, start API & UI servers, wait for readiness, open browser, and manage exit."""
    root = Path(project_root).resolve()
    print("=" * 60)
    print("[+] BRIF.AI — Yerel Konuşma Demosu Başlatıcı")
    print("=" * 60)
    print("[1/5] Kontroller yapılıyor...")

    results = run_all_preflight_checks(
        project_root=root,
        api_port=api_port,
        ui_port=ui_port,
        model_name=model_name,
        ollama_url=ollama_url,
        check_ollama=check_ollama,
    )

    failed = False
    for ok, msg in results:
        status_icon = "  [v]" if ok else "  [x]"
        print(f"{status_icon} {msg}")
        if not ok:
            failed = True

    if failed:
        print("\n[x] Ön kontroller başarısız oldu. İşlem güvenli biçimde durduruldu.")
        sys.exit(1)

    print("\n[2/5] Ön kontroller tamamlandı. Bağımlılıklar hazır.")

    python_executable = sys.executable
    manager = DemoProcessManager()

    # Guarantee process cleanup on exit or termination signal
    atexit.register(manager.stop_all)

    def _sig_handler(_signum: int, _frame: object) -> None:
        manager.stop_all()
        sys.exit(0)

    with contextlib.suppress(ValueError, OSError):
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, _sig_handler)

    # Determine UI directory
    ui_dir = root / "prototypes" / "conversation_ui_v0"

    print(f"[3/5] API başlatılıyor... (http://127.0.0.1:{api_port})")

    api_env = os.environ.copy()
    api_env["BRIF_AI_LLM_ENABLED"] = "true"
    api_env["BRIF_AI_LLM_PROVIDER"] = "ollama"
    api_env["BRIF_AI_LLM_BASE_URL"] = ollama_url
    api_env["BRIF_AI_LLM_MODEL"] = model_name
    api_env["BRIF_AI_LLM_TIMEOUT_SECONDS"] = str(int(llm_timeout))
    api_env["BRIF_AI_LLM_TEMPERATURE"] = "0"
    api_env["BRIF_AI_LLM_THINK"] = "false"
    api_env["BRIF_AI_LLM_NUM_PREDICT"] = str(num_predict)

    api_cmd = [
        python_executable,
        "-m",
        "uvicorn",
        "apps.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(api_port),
    ]
    api_proc = subprocess.Popen(
        api_cmd,
        cwd=root,
        env=api_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    manager.register_process("api", api_proc)

    print(f"[4/5] Arayüz başlatılıyor... (http://127.0.0.1:{ui_port})")
    ui_cmd = [
        python_executable,
        "-m",
        "http.server",
        str(ui_port),
        "-d",
        str(ui_dir),
    ]
    ui_proc = subprocess.Popen(
        ui_cmd,
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    manager.register_process("ui", ui_proc)

    api_url = f"http://127.0.0.1:{api_port}"
    ui_base_url = f"http://127.0.0.1:{ui_port}"
    full_ui_url = (
        f"{ui_base_url}/?apiBaseUrl=http%3A%2F%2F127.0.0.1%3A{api_port}"
        if api_port != 8000
        else ui_base_url
    )

    print("API hazırlık durumu ve LLM bağlantısı kontrol ediliyor...")
    api_ready, api_msg = wait_for_api_ready(
        api_url,
        timeout=15.0,
        expected_model=model_name,
        expected_provider="ollama",
    )

    if not api_ready:
        print(f"[x] {api_msg}")
        manager.stop_all()
        sys.exit(1)

    print("Arayüz hazırlık durumu kontrol ediliyor...")
    ui_ready = wait_for_ui_ready(ui_base_url, timeout=15.0)

    if not ui_ready:
        print("[x] Hata: Arayüz servisi zaman aşımı süresince hazır olamadı.")
        manager.stop_all()
        sys.exit(1)

    print("\n[5/5] BRIF.AI Yerel Konuşma Demosu Başarıyla Başlatıldı!")
    print("-" * 60)
    print(f"[*] Demo Adresi: {full_ui_url}")
    print(f"[*] API Adresi:  {api_url}")
    print("[*] Yerel yapay zekâ etkin")
    print(f"[*] Kullanılan sağlayıcı: Ollama ({ollama_url})")
    print(f"[*] Kullanılan model: {model_name}")
    print(f"[*] API zaman aşımı: {int(llm_timeout)} sn")
    print(f"[*] Tahmin token sınırı: {num_predict}")
    print("[*] Demo/fallback modu kullanılmıyor")
    print("[!] Güvenli Kapatma: Demoyu sonlandırmak için Ctrl+C tuşlarına basın.")
    print("-" * 60)

    if open_browser:
        with contextlib.suppress(Exception):
            webbrowser.open(full_ui_url)

    try:
        while True:
            time.sleep(1.0)
            if api_proc.poll() is not None or ui_proc.poll() is not None:
                print("\n[!] Sunucu süreçlerinden biri beklenmeyen şekilde durdu.")
                break
    except KeyboardInterrupt:
        print("\n\n[*] Kapatma isteği alındı. Süreçler temizleniyor...")
    finally:
        manager.stop_all()
        print("[v] BRIF.AI yerel demo süreçleri güvenle kapatıldı.")


def main() -> None:
    parser = argparse.ArgumentParser(description="BRIF.AI Yerel Demo Başlatıcı")
    parser.add_argument("--api-port", type=int, default=8000, help="API portu (varsayılan: 8000)")
    parser.add_argument("--ui-port", type=int, default=8080, help="UI portu (varsayılan: 8080)")
    parser.add_argument("--model", type=str, default="qwen3:4b-instruct", help="Model adı")
    parser.add_argument(
        "--ollama-url", type=str, default="http://127.0.0.1:11434", help="Ollama URL"
    )
    parser.add_argument("--no-browser", action="store_true", help="Tarayıcıyı otomatik açma")
    parser.add_argument("--no-ollama-check", action="store_true", help="Ollama kontrolünü atla")
    parser.add_argument(
        "--llm-timeout",
        type=float,
        default=DEFAULT_DEMO_LLM_TIMEOUT_SECONDS,
        help="LLM API zaman aşımı süresi saniye cinsinden",
    )
    parser.add_argument(
        "--num-predict",
        type=int,
        default=DEFAULT_DEMO_NUM_PREDICT,
        help=f"Maksimum tahmin token sayısı (varsayılan: {DEFAULT_DEMO_NUM_PREDICT})",
    )

    args = parser.parse_args()
    launch_demo(
        api_port=args.api_port,
        ui_port=args.ui_port,
        model_name=args.model,
        ollama_url=args.ollama_url,
        open_browser=not args.no_browser,
        check_ollama=not args.no_ollama_check,
        llm_timeout=args.llm_timeout,
        num_predict=args.num_predict,
    )


if __name__ == "__main__":
    main()
