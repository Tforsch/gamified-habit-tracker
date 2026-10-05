# Gamified Habit Tracker (Monorepo)

A collaborative web application designed to turn daily habits into an RPG-style adventure. Built by two mid-level software engineers with strict separation of concerns between Frontend and Backend workspaces.

---

## Architecture Overview

```text
.
├── backend/            # Backend Developer Workspace (Node.js/Express REST API)
│   ├── controllers/    # Request handlers & domain routing
│   ├── models/         # Relational database entities/schemas
│   ├── routes/         # Express endpoint routing
│   ├── services/       # Gamification engine (XP/HP) & cron schedulers
│   ├── package.json
│   └── server.js       # Backend entry point
├── frontend/           # Frontend Developer Workspace (Vanilla HTML/CSS/JS ES6+)
│   ├── public/         # Static images, icons, avatar presets
│   ├── scripts/        # Modular ES6 scripts (API client, State, UI renderer)
│   ├── styles/         # Modular CSS (design system, dashboard layouts)
│   └── index.html      # Main gamified dashboard HUD
├── API_CONTRACT.md     # Shared data contracts and API specifications
├── .gitignore
└── README.md
```

---

## Developer Quickstart

### Backend Setup (Node.js/Express)
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   Server defaults to `http://localhost:5000`.

### Frontend Setup (Vanilla HTML/CSS/JS)
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Serve static files using your preferred HTTP server (e.g. VS Code Live Server, `npx serve`, or Python):
   ```bash
   npx serve .
   ```
   Open `http://localhost:3000` (or the port specified by your runner).

---

## Branching & Merge Conflict Strategy
- Backend engineer works exclusively inside `/backend` and references `/API_CONTRACT.md`.
- Frontend engineer works exclusively inside `/frontend` and mocks or consumes endpoints per `/API_CONTRACT.md`.
- Any changes to API request/response structures require updating `/API_CONTRACT.md` before implementation.
