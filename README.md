# InsightFlow 🚀

> AI-Powered Business Analytics SaaS Platform

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React.js · Axios · Recharts |
| Backend | ASP.NET Core Web API (C#) · EF Core |
| Database | PostgreSQL |
| AI Engine | Python · Pandas · Llama 3 (Ollama) |
| DevOps | Docker · docker-compose |

---

## Quick Start

### Prerequisites
- [.NET 8 SDK](https://dotnet.microsoft.com/download)
- [Node.js 18+](https://nodejs.org/)
- [Python 3.11+](https://python.org/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Ollama](https://ollama.com/) (for local LLM)

---

## Phase 1 — Local Setup

### 1. Clone & open in VSCode
```bash
git clone <your-repo-url> InsightFlow
cd InsightFlow
code .
```

### 2. Start PostgreSQL via Docker
```bash
docker run --name insightflow-postgres \
  -e POSTGRES_DB=insightflow \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=secret \
  -p 5432:5432 -d postgres:15
```

### 3. Backend (ASP.NET Core)
```bash
cd backend
dotnet restore
dotnet ef migrations add InitialCreate
dotnet ef database update
dotnet run
# → http://localhost:5000
```

### 4. AI Engine (Python)
```bash
cd ai_engine
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --port 5001 --reload
# → http://localhost:5001
```

### 5. Frontend (React)
```bash
cd frontend
npm install
npm start
# → http://localhost:3000
```

### 6. Pull Llama 3 (one-time)
```bash
ollama pull llama3
```

---

## Or use Docker Compose (all services)
```bash
docker-compose up --build
```

---

## Project Structure

```
InsightFlow/
├─ backend/           # ASP.NET Core Web API
├─ frontend/          # React.js app
├─ ai_engine/         # Python AI pipeline + FastAPI
├─ database/          # SQL migrations
├─ docker-compose.yml
└─ README.md
```

---

## Development Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Foundation & Setup | Done |
| 2 | Backend & Database | Done |
| 3 | AI Engine | Done |
| 4 | Frontend Dashboard | ⏳ Upcoming |
| 5 | Integration & Testing | ⏳ Upcoming |
| 6 | Docker & Deployment | ⏳ Upcoming |
