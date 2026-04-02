# ObserveProctor EXE Application

Windows desktop proctoring client for secure coding/exam sessions.

This application provides a guided exam flow (login, identity, terms, secure setup, exam), local runtime hardening, telemetry/evidence capture, and signed API integration with backend services.

## What This App Does

- Runs a full-screen proctored exam experience with PyQt6.
- Performs identity/session bootstrap and exam lifecycle APIs.
- Applies security controls during exam runtime:
  - keyboard and shell lockdown
  - suspicious process monitoring and optional auto-termination
  - optional network isolation/firewall restrictions
  - tamper checks and integrity monitoring
- Captures proctoring signals:
  - vision-based liveness and gaze behavior
  - audio-based speech/noise detection
  - evidence screenshots/webcam frames with signed uploads
- Supports production packaging into a single Windows executable.

## High-Level Architecture

```mermaid
flowchart LR
    UI[PyQt6 UI Flow]\nmain.py
    CTRL[Exam Controller]\nexam_controller.py
    CORE[Proctoring Core]\ncore/*
    API[Secure API Client]\napi_client.py
    BACKEND[Backend Services]\nAuth Exam JIT Report
    MOCK[Local Mock Server]\nserver/mock_server.py

    UI --> CTRL
    CTRL --> API
    CTRL --> CORE
    API --> BACKEND
    UI --> CORE
    MOCK --> BACKEND
```

## Runtime Flow

1. Application starts from `main.py` and loads environment values via `env_loader.py`.
2. User signs in through `ui/login_screen.py`.
3. App authenticates and receives session nonce/exam bootstrap data via `api_client.py`.
4. `core/proctoring_service.py` starts monitoring (vision/audio/process/integrity).
5. During exam, telemetry and evidence are sent to backend endpoints with HMAC-signed payloads.
6. Final submission is posted; server-side report ingestion may be triggered.

## Project Structure

```text
EXE-Application/
|- main.py                      # Desktop entrypoint and UI screen orchestration
|- exam_controller.py           # UI-to-backend exam bridge
|- api_client.py                # Signed HTTP client for auth/exam/telemetry/evidence
|- build.py                     # Production build pipeline (Nuitka with PyInstaller fallback)
|- build.ps1 / build.bat        # Windows convenience build scripts
|- run_server.bat               # Starts local mock server
|- env_loader.py                # .env loader for dev and frozen runtime
|- ENV_SECURITY.md              # Notes on embedding .env into packaged EXE
|- core/
|  |- proctoring_service.py
|  |- vision_proctor.py
|  |- audio_proctor.py
|  |- lockdown.py
|  |- process_monitor.py
|  |- integrity.py / hasher.py
|  |- snapshot_uploader.py
|  |- telemetry.py
|  |- secure_audit_log.py
|  |- anti_tamper.dll
|- ui/                          # Screens and components
|- server/
|  |- mock_server.py            # Local secure backend mock
|  |- db.py                     # DB bootstrap/access
```

## Tech Stack

- Python 3.12+
- PyQt6 desktop UI
- OpenCV + MediaPipe for vision checks
- NumPy, sounddevice for audio checks
- psutil/pywin32/WMI for Windows process and OS controls
- Requests/urllib for backend communication
- PyInstaller and Nuitka for packaging

## Prerequisites

- OS: Windows 10/11 (required for lockdown and Windows security hooks)
- Python 3.12 (recommended due to included compiled extensions)
- Webcam and microphone
- Network access to configured backend URL
- Optional for local server mode: PostgreSQL configured via `server/.env`

## Local Development Setup

1. Create and activate a virtual environment.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Create environment files.

- Root `.env` for desktop app runtime/build.
- `server/.env` for local mock server runtime.

4. Start local mock server.

```bat
run_server.bat
```

5. Run desktop app in development mode.

```powershell
python main.py
```

## Production Build

### Recommended

```powershell
python build.py --clean
```

### Backend selection

```powershell
python build.py --clean --backend nuitka
python build.py --clean --backend pyinstaller
```

By default, the builder uses Nuitka and falls back to PyInstaller if needed.

### Script wrappers

```powershell
.\build.ps1
```

```bat
build.bat
```

### Build output

- `dist/ObserveProctor.exe`
- `dist/.env.example` (copied only when root `.env.example` exists)

Note: The build process embeds `.env` into the EXE payload for harder runtime tampering. See `ENV_SECURITY.md`.

## Environment Variables

Important variables used by the app and/or local mock server.

| Variable | Required | Purpose |
|---|---|---|
| `OBSERVE_SERVER_URL` | Yes | Canonical backend URL for desktop app (HTTPS, approved Lightning host enforced). |
| `OBSERVE_BACKEND_URL` | Optional | Legacy fallback backend URL key. |
| `OBSERVE_PROCTOR_SECRET` | Yes | Shared secret for HMAC signatures (minimum 24 chars enforced). |
| `OBSERVE_ADDITIONAL_WHITELIST_URLS` | Optional | Additional allowed outbound URLs for restricted mode. |
| `OBSERVE_TLS_PIN_SHA256` | Optional | Certificate pin value for stricter TLS checks. |
| `OBSERVE_ENABLE_KEYBOARD_LOCKDOWN` | Optional | Enable keyboard/shell lockdown layer. |
| `OBSERVE_STRICT_OS_LOCKDOWN` | Optional | Apply stricter shell policy controls during exam. |
| `OBSERVE_ENABLE_FULL_LOCKDOWN` | Optional | Enable full runtime process suppression mode. |
| `OBSERVE_ENABLE_RUNTIME_AUTO_TERMINATE` | Optional | Auto-kill suspicious processes when detected. |
| `OBSERVE_FORCE_EXAM_TOPMOST` | Optional | Force exam window topmost behavior. |
| `OBSERVE_FOCUS_GUARD_INTERVAL_MS` | Optional | Focus enforcement timer interval. |
| `SERVER_PORT` | Local server | Port for `server/mock_server.py` (default 8080). |
| `DATABASE_URL` | Local server | Database connection for mock server data. |
| `SUPABASE_URL` | Optional | Supabase storage endpoint for evidence/log uploads. |
| `SUPABASE_SERVICE_ROLE_KEY` | Optional | Supabase service key for storage operations. |
| `EVIDENCE_BUCKET` | Optional | Supabase evidence bucket name. |
| `EXAM_LOGS_BUCKET` | Optional | Supabase exam logs bucket name. |
| `JIT_SERVICE_BASE_URL` | Optional | JIT service base URL used by mock server integration. |
| `REPORT_SERVICE_BASE_URL` | Optional | Report generation service base URL used by mock server integration. |

## API Surface Used By Desktop Client

The client in `api_client.py` calls backend endpoints for:

- Health and auth: `/health`, `/v1/auth/login`
- Session and bootstrap: `/v1/session/nonce`, `/v1/exam/bootstrap`
- Exam progression: answer save, coding run/submit, transitions
- Telemetry and evidence: telemetry snapshots, screenshot/webcam evidence uploads
- Completion: final exam submission

All sensitive exam-session calls are signed and include anti-replay metadata (sequence/timestamp/payload hash patterns).

## Security Model

- Strong backend URL validation in `core/backend_config.py`.
- HMAC signature checks using `OBSERVE_PROCTOR_SECRET`.
- Replay protection via sequence/timestamp/nonce controls.
- Runtime hardening controls in `core/lockdown.py` and `core/proctoring_service.py`.
- Process monitoring and suspicious keyword checks.
- Optional firewall/network restrictions.
- Tamper-evident audit logging chain via `core/secure_audit_log.py`.
- Packaged `.env` embedding to reduce post-build config tampering (`ENV_SECURITY.md`).

## GitHub Publishing Checklist

Before publishing this folder or repository:

1. Remove all real secrets from `.env` and `server/.env`.
2. Never commit service keys/tokens (backend secret, Supabase keys, DB credentials).
3. Exclude generated/runtime artifacts:
   - `venv/`
   - `dist/`
   - `build/`
   - `logs/`
   - `server/log.txt`
   - `server/evidence_frames/`
   - `__pycache__/` and `*.pyc`
4. Confirm license compatibility for bundled binary artifacts and model files.
5. Verify no internal endpoint URLs or org-specific IDs remain in committed config examples.

Suggested `.gitignore` entries:

```gitignore
venv/
dist/
build/
logs/
server/log.txt
server/evidence_frames/
__pycache__/
*.pyc
.env
server/.env
build_log.txt
```

## Troubleshooting

- Build fails with backend URL error:
  - Set `OBSERVE_SERVER_URL` to an HTTPS Lightning AI host allowed by validation.
- Build fails with secret error:
  - Set `OBSERVE_PROCTOR_SECRET` with at least 24 characters.
- Camera/vision unavailable:
  - Ensure webcam access permissions and required OpenCV/MediaPipe packages are installed.
- Lockdown features not working:
  - Run on supported Windows environment with required privileges.

## Related Notes

- Environment embedding and runtime policy hardening: `ENV_SECURITY.md`
- Local backend behavior and endpoints: `server/mock_server.py`

## Environment Verification (Required)

You must verify this service has a valid `.env` before startup.

```powershell
Test-Path "EXE-Application/.env"
Select-String -Path "EXE-Application/.env" -Pattern "OBSERVE_SERVER_URL|OBSERVE_PROCTOR_SECRET"
```

If the file is missing, create it from `EXE-Application/.env.example` and populate real values.

## Repository Structure (Workspace Context)

```text
observe-github/
|- EXE-Application/             <-- current service
|- Web_Server/
|- Coding_Environment_Service/
|- Core_Backend_Services/
|  |- JIT_Generator_Service/
|  |- LLM_Morphing_Service/
|- Rendering_service/
|  |- report_agent/
|- Report_Generation_service/
|- observe/
```

