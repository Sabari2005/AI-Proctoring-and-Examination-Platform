# Environment Files Installation Guide (Google Drive -> Project)

This guide explains how to place environment files from Google Drive into the correct service folders in this repository.

Google Drive source:
https://drive.google.com/drive/folders/1IYAY8XZIZqugufNIZ6o6T1TchlIgKPW9?usp=sharing

## Prerequisites

- OS: Windows (PowerShell)
- Repo path: E:\virtusa-github
- You already have `.env.example` files in every service folder.

## Target Files and Locations

You must create these `.env` files:

1. `Web_Server/.env`
2. `Coding_Environment_Service/.env`
3. `Core_Backend_Services/JIT_Generator_Service/.env`
4. `Core_Backend_Services/LLM_Morphing_Service/.env`
5. `Rendering_service/report_agent/.env`
6. `Report_Generation_service/.env`
7. `EXE-Application/.env`

## Step 1: Download Credentials From Google Drive

1. Open the Drive link.
2. Download the credentials package (or all required `.env` files).
3. Extract to a local folder, for example:
   - `C:\Users\<YourUser>\Downloads\Workspace_Credentials`

Expected extracted structure (recommended):

- `Workspace_Credentials/Web_Server_Credentials/.env`
- `Workspace_Credentials/Coding_Environment_Service_Credentials/.env`
- `Workspace_Credentials/Core_Backend_Services/jit_Generator/.env`
- `Workspace_Credentials/Core_Backend_Services/llm_morphing/.env`
- `Workspace_Credentials/Rendering_Service/.env`
- `Workspace_Credentials/Report_Generation_Service_Credentials/.env`
- `Workspace_Credentials/EXE_Application_Credentials/.env`

## Step 2: Copy .env Files Into Services (PowerShell)

Run these commands from `E:\virtusa-github`.

```powershell
$CredRoot = "C:\Users\<YourUser>\Downloads\Workspace_Credentials"

Copy-Item "$CredRoot\Web_Server_Credentials\.env" "E:\virtusa-github\Web_Server\.env" -Force
Copy-Item "$CredRoot\Coding_Environment_Service_Credentials\.env" "E:\virtusa-github\Coding_Environment_Service\.env" -Force
Copy-Item "$CredRoot\Core_Backend_Services\jit_Generator\.env" "E:\virtusa-github\Core_Backend_Services\JIT_Generator_Service\.env" -Force
Copy-Item "$CredRoot\Core_Backend_Services\llm_morphing\.env" "E:\virtusa-github\Core_Backend_Services\LLM_Morphing_Service\.env" -Force
Copy-Item "$CredRoot\Rendering_Service\.env" "E:\virtusa-github\Rendering_service\report_agent\.env" -Force
Copy-Item "$CredRoot\Report_Generation_Service_Credentials\.env" "E:\virtusa-github\Report_Generation_service\.env" -Force
Copy-Item "$CredRoot\EXE_Application_Credentials\.env" "E:\virtusa-github\EXE-Application\.env" -Force
```

## Step 3: Verify Installation

Run:

```powershell
Get-ChildItem -Path "E:\virtusa-github" -Recurse -Filter ".env" -File |
Select-Object -ExpandProperty FullName |
Sort-Object
```

Expected output should include exactly these 7 files:

- `E:\virtusa-github\Web_Server\.env`
- `E:\virtusa-github\Coding_Environment_Service\.env`
- `E:\virtusa-github\Core_Backend_Services\JIT_Generator_Service\.env`
- `E:\virtusa-github\Core_Backend_Services\LLM_Morphing_Service\.env`
- `E:\virtusa-github\Rendering_service\report_agent\.env`
- `E:\virtusa-github\Report_Generation_service\.env`
- `E:\virtusa-github\EXE-Application\.env`

## Step 4: Quick Validation Per Service

Optional checks to ensure all required keys are present:

```powershell
# Example: check key presence in one env file
Select-String -Path "E:\virtusa-github\Web_Server\.env" -Pattern "DATABASE_URL|SUPABASE_URL|SUPABASE_KEY"

Select-String -Path "E:\virtusa-github\Coding_Environment_Service\.env" -Pattern "SECRET_KEY|DATABASE_URL|REDIS_URL"

Select-String -Path "E:\virtusa-github\Core_Backend_Services\JIT_Generator_Service\.env" -Pattern "GROQ_API_KEY|GEMINI_API_KEY"

Select-String -Path "E:\virtusa-github\Core_Backend_Services\LLM_Morphing_Service\.env" -Pattern "GROQ_API_KEY|GEMINI_API_KEY"

Select-String -Path "E:\virtusa-github\Rendering_service\report_agent\.env" -Pattern "GROQ_API_KEY|SUPABASE_SERVICE_ROLE_KEY"

Select-String -Path "E:\virtusa-github\Report_Generation_service\.env" -Pattern "DATABASE_URL|SUPABASE_SERVICE_ROLE_KEY"

Select-String -Path "E:\virtusa-github\EXE-Application\.env" -Pattern "VIRTUSA_SERVER_URL|VIRTUSA_PROCTOR_SECRET"
```

## Troubleshooting

1. `Cannot find path ...` while copying:
- Confirm extracted Drive folder path in `$CredRoot`.
- Confirm the downloaded folder names match this guide exactly.

2. File copied but app still fails:
- Ensure file name is exactly `.env` (not `.env.txt`).
- Ensure no extra quotes/trailing characters were added to values.

3. Missing keys:
- Compare each `.env` with corresponding `.env.example` in the same service.

