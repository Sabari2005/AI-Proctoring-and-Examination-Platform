# .env Security Model

## Issue Fixed

Previously, the `.env` file was copied to the `dist/` folder as an external file after building the EXE. This allowed users to modify security settings at runtime, including:

- `OBSERVE_ENABLE_KEYBOARD_LOCKDOWN`
- `OBSERVE_STRICT_OS_LOCKDOWN`  
- `OBSERVE_ENABLE_FULL_LOCKDOWN`
- `OBSERVE_ENABLE_RUNTIME_AUTO_TERMINATE`
- Any other security toggles

This was a critical security vulnerability.

## Solution Implemented

### Build-time Changes (build.py)
- Added `--add-data` directive to bundle `.env` into the one-file PyInstaller EXE
- Removed the `shutil.copy2(ENV_FILE, DIST_DIR / ".env")` line that exposed `.env`
- `.env` is now embedded inside the executable, making external modification impossible

### Runtime Changes (env_loader.py)
- Updated to load `.env` from `sys._MEIPASS` when running as a frozen executable
- `sys._MEIPASS` points to PyInstaller's temporary extraction directory
- Fallback to development paths when not frozen (for development/testing)

### Distribution
- Users no longer receive `.env` file in the `dist/` folder
- `.env.example` is still copied for reference (optional - shows what settings are available)
- No security secrets exposed in deployment

## Security Benefits

1. **Immutable Configuration**: Users cannot modify deployed security settings
2. **No External Exposure**: Security keys (OBSERVE_PROCTOR_SECRET) are embedded in binary
3. **Integrity**: Even if someone extracts the EXE, the `_internal` path structure makes tampering harder
4. **Audit Trail**: Tamper detection and HMAC-chained audit logging will catch any modified app behavior

## Deployment

After building with `build.py --clean`:
- `dist/ObserveProctor.exe` - Single file executable with embedded `.env`
- `dist/.env.example` - Reference file (optional, for support)
- No other files needed for deployment


## Development Testing

For development, `env_loader.py` still supports loading from:
1. `ENV_FILE` environment variable
2. Project root `.env` (for running dev scripts)
3. Current working directory `.env`

Set `ENV_FILE=/path/to/.env` to override for development.

