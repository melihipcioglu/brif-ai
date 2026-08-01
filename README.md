# BRIF.AI

BRIF.AI architectural decision support platform.

## Requirements

- Python 3.12

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Developer Commands

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests apps
python -m pytest

```

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
and 3000. The Ollama port must not be exposed to the public network.

### 5. Disabled/demo mode

`BRIF_AI_LLM_ENABLED=false` is the default. In this mode the existing local demo
conversation remains available and the UI states:
`Yerel yapay zekâ bağlantısı devre dışı. Demo konuşma modu kullanılıyor.`
Project state and conversation history are preserved. Provider failures while enabled do
not trigger demo fallback.

### Local data and hardware

Conversation input is sent from the browser to the BRIF.AI FastAPI backend and then only
to the configured loopback Ollama service. Full conversations are not logged by this
integration. Model responses are schema- and policy-validated before safe DOM rendering.

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

