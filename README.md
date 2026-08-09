# BRIF.AI

BRIF.AI architectural decision support platform. The repository is currently a technical
MVP and local-demo implementation; it is not a complete or production-ready product.

## Requirements

- Python 3.12

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,demo]"
```

## Demoyu Başlatma ve Kapatma

BRIF.AI yerel konuşma demosunu Windows üzerinde tek bir komutla başlatabilirsiniz:

```powershell
.\run_demo.ps1
```

Bu komut sırasıyla gerekli kontrolleri yapar (proje dizini, sanal ortam, Python paketleri,
Ollama servisi, model ve portlar). Tarayıcı yalnız API health sonucu `ok` olduğunda; yani
Ollama erişilebilir ve seçilen model gerçekten yüklüyken açılır.

- **Farklı portlar ile başlatma:**
  ```powershell
  .\run_demo.ps1 -ApiPort 8005 -UiPort 8090
  ```
- **Yalnız hızlı Ollama ön kontrolünü atlama:**
  ```powershell
  .\run_demo.ps1 -SkipOllamaPreflight
  ```
  Bu seçenek gerçek LLM hazırlık kontrolünü atlamaz ve demo/fallback moduna geçmez.
  Eski `-NoOllamaCheck` adı geriye uyumluluk alias'ı olarak kabul edilir.
  Python başlatıcısında eşdeğer seçenek `--skip-ollama-preflight`; eski
  `--no-ollama-check` adı burada da geriye uyumluluk için desteklenir.
- **Güvenli Kapatma:**
  Demoyu sonlandırmak için komut penceresinde `Ctrl+C` tuşlarına basmanız yeterlidir. Yalnızca demo için başlatılan sunucular güvenle kapatılır.

## Developer Commands

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests apps
python -m pytest
```

GitHub Actions bu birim/statik kontrol paketini çalıştırır; CI içinde Ollama kurulmaz ve
4B model indirilmez. Gerçek model doğrulaması aşağıdaki isteğe bağlı yerel smoke test ile
yapılır:

```powershell
.venv\Scripts\python.exe scripts\smoke_test_real_ollama.py --model qwen3:4b-instruct
```

Ollama veya seçilen model yoksa komut açıkça `SKIPPED / prerequisites missing` bildirir.
Ön koşullar bulunduğu hâlde şema, güvenlik veya gerçek inference doğrulaması başarısızsa
non-zero exit code üretir. Sabit test istemi ve ham model cevabı loglanmaz; yalnız model adı,
toplam süre ve mevcutsa token metrikleri yazılır.

## Local LLM Conversation MVP

The conversation backend uses a provider-neutral `LocalLLMProvider` boundary. The current
adapter is Ollama over local HTTP; the service and API do not know Ollama request formats.
Future `LlamaCppProvider` or `VLLMProvider` adapters can implement the same boundary.
Model output is constrained with the Pydantic-generated JSON Schema in Ollama's `format`
field, validated again with Pydantic, and then checked against the active project context.
The model can only suggest an action. It cannot mutate the plan, SVG geometry, or
`ContextStateMachine`; approval creates a proposal audit record only.

No OpenAI API, API key, paid external model, Ollama Cloud, or Kimi K3 Cloud is used by this
integration. The default Ollama address is the loopback-only
`http://127.0.0.1:11434`.

### 1. Install Ollama

Install the desktop/server package from [Ollama's official download page](https://ollama.com/download).
Start the local service if it is not already running:

```powershell
ollama serve
```

BRIF.AI never downloads a model automatically. Selecting and downloading a model is a
separate user decision; if needed, run `ollama pull <model-name>` yourself only after
choosing an appropriate model.

### 2. Verify Ollama and list installed models

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
ollama ls
```

The backend also exposes installed models at
`GET http://127.0.0.1:8000/api/v1/llm/models`.

`GET /api/v1/health` uses one model-list request and returns one of these typed states:

- `ok`: local LLM is enabled, Ollama is reachable, and the selected model is installed.
- `degraded`: the API runs, but LLM is disabled, no model is selected, the model is absent,
  or the provider response cannot be fully validated.
- `unavailable`: Ollama cannot be reached or the health request times out.

### 3. Select a model

Use `.env.example` as a reference and set the variables in the shell that starts the
backend. The model name must exactly match an entry returned by `ollama ls`:

```powershell
$env:BRIF_AI_LLM_ENABLED = "true"
$env:BRIF_AI_LLM_PROVIDER = "ollama"
$env:BRIF_AI_LLM_BASE_URL = "http://127.0.0.1:11434"
$env:BRIF_AI_LLM_MODEL = "<installed-model-name>"
$env:BRIF_AI_LLM_TIMEOUT_SECONDS = "120"
$env:BRIF_AI_LLM_TEMPERATURE = "0"
```

No model name is hard-coded. If no model is selected, the API returns a clear selection
message; if the selected model is absent or Ollama is unreachable, it returns that real
error and does not silently switch to demo output.

### 4. Start backend and frontend

```powershell
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
python -m http.server 8080 --directory prototypes/conversation_ui_v0
```

Open `http://127.0.0.1:8080`. CORS is limited to localhost/127.0.0.1 on ports 8080
and 3000 by default. The launcher sets `BRIF_AI_UI_ORIGIN` for a custom `UiPort`; the API
validates that it is an `http` origin on `localhost` or `127.0.0.1` and permits both host
spellings for that same port. Wildcards and external hosts are rejected. The Ollama port
must not be exposed to the public network.

### 5. Disabled/demo mode

`BRIF_AI_LLM_ENABLED=false` is the default. In this mode the existing local demo
conversation remains available and the UI states:
`Yerel yapay zekâ bağlantısı devre dışı. Demo konuşma modu kullanılıyor.`
Project state and conversation history are preserved. Provider failures while enabled do
not trigger demo fallback. `run_demo.ps1` explicitly enables the real local model, so a
timeout, unavailable provider, or missing model stops startup instead of producing a demo
answer.

### Local data and hardware

In the current launcher and API implementation, conversation input is sent from the browser
to the BRIF.AI FastAPI backend and then only to a validated loopback Ollama URL. Full prompts
and raw model responses are not logged by this integration. `.demo_logs` captures server
process diagnostics without adding prompt or raw-response logging; API access logging is
disabled. Model responses are schema- and policy-validated before safe DOM rendering.

Strong model selection depends on the computer's GPU, VRAM, RAM, and storage capacity.
The largest open model will not run on every computer. BRIF.AI's provider layer preserves
the application code when the local model or serving engine changes. An appropriate model
will be selected after the first hardware assessment.

## Streamlit Demo

```powershell
py -3.13 -m pip install -e ".[dev,demo]"
py -3.13 -m streamlit run apps/daily_routines_demo.py
```

## Pre-commit

```powershell
python -m pre_commit install
python -m pre_commit run --all-files
```
