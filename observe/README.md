# Observe Frontend

Observe is a React + Vite frontend for a proctoring and assessment platform. It includes:
- public marketing pages,
- candidate authentication and onboarding,
- candidate dashboard with exam registration and launch-code flow,
- admin operations dashboard,
- superadmin tenant and platform governance dashboard.

## Table of Contents
- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [How It Works](#how-it-works)
- [Routing Map](#routing-map)
- [Project Structure](#project-structure)
- [Backend Integration](#backend-integration)
- [Getting Started](#getting-started)
- [Build and Preview](#build-and-preview)
- [Configuration Notes](#configuration-notes)
- [Known Constraints](#known-constraints)

## Overview
This frontend is built as a single-page app with role-oriented user journeys:
- Candidate: register, login, complete onboarding, discover exams, register, launch exam, review history and offers.
- Admin: manage exams, sections, questions, candidates, monitoring, and result publication.
- Superadmin: manage organizations, global users, monitoring, and platform-level controls.

The app uses React Router and renders two layout modes:
- Marketing layout with global navigation and footer.
- Isolated application screens (onboarding and dashboards) without global marketing chrome.

## Tech Stack
- React 19
- Vite 7
- React Router DOM 7
- Tailwind CSS 4 (via @tailwindcss/vite)
- Framer Motion
- Recharts
- Lenis smooth scrolling
- Lucide icons
- ESLint 9 flat config

## How It Works
1. App bootstraps in src/main.jsx with BackendProvider and BrowserRouter.
2. App routes are defined in src/App.jsx.
3. Marketing routes are wrapped with MainLayout (Navbar + Footer).
4. Candidate and admin/superadmin routes are standalone full-screen app surfaces.
5. Backend URL is provided through context from src/contexts/BackendContext.jsx.
6. Authentication tokens and candidate/admin identity are stored in localStorage.
7. Dashboards call backend APIs directly with fetch and bearer tokens.

## Routing Map
Public and marketing pages:
- /
- /pricing
- /customers
- /docs
- /blog
- /about
- /community
- /login
- /register
- /contact

Candidate app pages:
- /onboarding
- /dashboard

Admin pages:
- /admin/login
- /admin/dashboard

Superadmin pages:
- /superadmin/login
- /superadmin/dashboard

## Project Structure
- src/main.jsx: app entrypoint and provider setup.
- src/App.jsx: routing, global layout split, Lenis setup.
- src/contexts/BackendContext.jsx: backend base URL context.
- src/components/: reusable marketing components.
- src/pages/: route-level pages (marketing + candidate + admin + superadmin).
- src/index.css: Tailwind import and custom utility layer.
- src/App.css: legacy Vite starter CSS (currently not used by main screens).

## Backend Integration
Base URL source:
- src/contexts/BackendContext.jsx exports BACKEND_URL currently set to http://127.0.0.1:8000

Primary API domains used by the frontend:
- Candidate auth and profile:
	- POST /auth/register
	- POST /auth/login
	- GET /auth/me
	- POST /auth/change-password
	- GET /candidate/profile/{candidate_id}
	- PUT /candidate/profile
	- POST /candidate/profile-photo
- Candidate onboarding:
	- POST /candidate/account
	- POST /candidate/identity
	- POST /candidate/profile
	- POST /candidate/links
- Candidate exams and results:
	- GET /candidate/exams/discover
	- GET /candidate/exams/upcoming
	- POST /candidate/exams/{exam_id}/register
	- DELETE /candidate/exams/{exam_id}/register
	- POST /candidate/exams/{exam_id}/launch-code
	- GET /candidate/history/results
	- GET /candidate/offers/{result_id}/download
- Candidate notifications:
	- GET /auth/notifications/me
	- PATCH /auth/notifications/{notification_id}/read
- Admin:
	- POST /auth/admin/login
	- GET /admin/exams
	- POST /admin/exams
	- PATCH /admin/exams/{exam_id}
	- DELETE /admin/exams/{exam_id}
	- GET /admin/exams/{exam_id}/sections
	- POST /admin/exams/{exam_id}/sections
	- PATCH /admin/exams/sections/{section_id}
	- DELETE /admin/exams/sections/{section_id}
	- GET /admin/exams/sections/{section_id}/questions
	- POST /admin/exams/sections/{section_id}/questions
	- PATCH /admin/exams/questions/{question_id}
	- DELETE /admin/exams/questions/{question_id}
	- GET /admin/exams/results
	- GET /admin/exams/results/candidates
	- POST /admin/exams/results/publish
	- GET /admin/exams/results/{result_id}/report-link
- Superadmin:
	- POST /auth/superadmin/login
	- GET /auth/superadmin/organizations
	- POST /auth/superadmin/register-organization
	- PATCH /auth/superadmin/organizations/{vendor_id}
	- DELETE /auth/superadmin/organizations/{vendor_id}
	- GET /auth/superadmin/users
	- PATCH /auth/superadmin/users/{user_id}
	- DELETE /auth/superadmin/users/{user_id}

## Getting Started
Requirements:
- Node.js 20+
- npm 10+

Install dependencies:

```bash
npm install
```

Run development server:

```bash
npm run dev
```

Default Vite local URL is shown in terminal (typically http://localhost:5173).

## Build and Preview
Create production build:

```bash
npm run build
```

Preview built app:

```bash
npm run preview
```

Lint source:

```bash
npm run lint
```

## Configuration Notes
- The backend base URL is hardcoded in src/contexts/BackendContext.jsx.
- For multi-environment deployment, prefer replacing this with Vite environment variables (for example import.meta.env.VITE_BACKEND_URL).
- Candidate token key: access_token
- Admin token key: admin_token
- Superadmin token key: superadmin_token

## Known Constraints
- Some views still contain placeholder data blocks for UX scaffolding and are marked as under development in code.
- src/App.css includes default template styles that are mostly superseded by Tailwind classes.
- The app assumes backend CORS and endpoint contracts match the listed paths.

## Environment Verification (Required)

This frontend currently uses a hardcoded backend URL in `src/contexts/BackendContext.jsx`.
Before startup, verify backend configuration is present through one of these methods:

```powershell
# Current implementation check (hardcoded backend URL)
Select-String -Path "observe/src/contexts/BackendContext.jsx" -Pattern "BACKEND_URL"

# Optional env-based approach if you migrate to Vite env vars
Test-Path "observe/.env"
Test-Path "observe/.env.local"
```

## Repository Structure (Workspace Context)

```text
observe-github/
|- observe/                     <-- current service
|- Web_Server/
|- Coding_Environment_Service/
|- Core_Backend_Services/
|  |- JIT_Generator_Service/
|  |- LLM_Morphing_Service/
|- Rendering_service/
|  |- report_agent/
|- Report_Generation_service/
|- EXE-Application/
```


