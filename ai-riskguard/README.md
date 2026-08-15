# AI RiskGuard — Enterprise AI Governance Platform

AI RiskGuard is an Enterprise AI Governance Research & Assessment Platform developed for the **MODUS Enterprise AI Build Challenge (Assignment 7)**.

It provides a repeatable, dynamic governance assessment engine that evaluates newly registered enterprise AI use cases across **10 core risk dimensions**, backed by real-time public source research and evidence retrieval without proprietary LLM vendor lock-in.

---

## 🏗️ System Architecture

```
Streamlit UI (Port 8501)
     │
     ▼ (HTTP / REST API)
FastAPI Backend (Port 8000)
     │
     ├── Core & Config (Pydantic Settings)
     ├── API Routers (/api/v1/health, /api/v1/use-cases, /api/v1/research, /api/v1/assessments)
     ├── Governance Assessment Engine (Rule-based, repeatable scoring)
     ├── Research Service (Dynamic queries + DuckDuckGo search + fetch)
     ├── Source Classifier (Domain/URL heuristics to categorise law, standards, vendor, etc.)
     ├── Evidence Service (Verbatim sentence extraction + conflict detection)
     ├── TF-IDF Retrieval Layer (Local scikit-learn document indexing & search)
     ├── AI Provider Abstraction (Optional Ollama summariser / Fallback extractor)
     └── SQLAlchemy ORM Layer
           │
           ▼
SQLite Database (data/airiskguard.db)
```

---

## 📁 Repository Structure

```
ai-riskguard/
├── backend/
│   ├── main.py                # FastAPI application entrypoint & lifecycle hooks
│   ├── api/                   # REST API routes
│   │   └── v1/
│   │       ├── health.py      # Health-check & DB status endpoint
│   │       ├── use_cases.py   # AI Use Case creation & management routes
│   │       ├── assessments.py # Governance assessment execution & log retrieval
│   │       └── research.py    # Trigger research, view sources & evidence
│   ├── core/                  # Project configuration & settings
│   │   ├── config.py          # Settings including AI provider and research limits
│   │   └── governance_config.py # Dimension config and risk level thresholds
│   ├── database/              # SQLAlchemy session & connection management
│   │   └── session.py
│   ├── models/                # SQLAlchemy ORM database models
│   │   └── models.py
│   ├── schemas/               # Pydantic data validation & serialization schemas
│   │   └── schemas.py
│   └── services/              # Business logic & modular services
│       ├── ai_provider.py     # AI Model Provider Abstraction (Ollama / Fallback)
│       ├── assessment_service.py # Use case & assessment workflow orchestrator
│       ├── governance_engine.py # Deterministic scoring & weighting engine
│       ├── research_service.py # Dynamic web query, fetching, cleaning & pipeline orchestrator
│       ├── source_classifier.py # Rule-based URL categorization & credibility rating
│       ├── evidence_service.py # Sentence extraction, conflict flagging & confidence scoring
│       └── retrieval_service.py # TF-IDF local text vectorization & search
│
├── frontend/
│   └── streamlit_app.py       # Streamlit multi-tab enterprise dashboard UI
│
├── tests/                     # Test suite
│   ├── conftest.py            # In-memory SQLite fixtures & TestClient configuration
│   ├── test_health.py         # Health check API unit tests
│   ├── test_database.py       # Database CRUD & seed validation tests
│   └── test_research.py       # Step 3 research & evidence unit/integration tests
│
├── data/                      # Persistent SQLite database storage
├── docs/                      # Technical documentation
│   └── research-architecture.md # Traceability diagram & detailed research steps
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore
└── README.md
```

---

## 🗄️ Database Entities

1. **`AIUseCase`**: Stores registered AI use cases.
2. **`Assessment`**: Governance evaluation runs with overall score, level, and execution status.
3. **`RiskDimension`**: The 10 core governance risk dimensions.
4. **`AssessmentResult`**: Per-dimension evaluation scores and detailed reasoning.
5. **`ResearchQuery`**: Automatically generated search queries mapped to dimensions.
6. **`Source`**: Legal & regulatory source citations (URL, Title, Publisher, Type, Credibility).
7. **`Evidence`**: Verbatim evidence snippets extracted from research sources.
8. **`AssessmentEvidence`**: Join table linking assessments to supporting evidence.
9. **`Recommendation`**: Actionable remediation guidance associated with assessments.

---

## ⚡ Quickstart Guide

### 1. Environment Setup

```bash
# Clone repository and navigate to folder
cd ai-riskguard

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 2. Run the FastAPI Backend Server

```bash
# From the root directory (ai-riskguard):
uvicorn backend.main:app --reload
```
- API Documentation (Swagger UI): `http://localhost:8000/docs`
- API Health Endpoint: `http://localhost:8000/api/v1/health`

### 3. Run the Streamlit Frontend UI

```bash
# Open a second terminal, activate venv, then run:
streamlit run frontend/streamlit_app.py
```
- Frontend Dashboard: `http://localhost:8501`

### 4. Run Unit Tests

```bash
# Run pytest test suite
python -m pytest -v
```

---

## 🔄 Component Interaction Flow (Research-Backed Flow)

1. **User Request**: User submits an AI Use Case details in the Streamlit UI.
2. **API Dispatch**: Streamlit sends a REST request to FastAPI (`POST /api/v1/use-cases`).
3. **Research Run**: Streamlit triggers `POST /api/v1/assessments/{use_case_id}/research-backed`.
4. **Query Generation**: `ResearchService` dynamically constructs search terms from use case attributes.
5. **Retrieval**: System queries DuckDuckGo, fetches page text, removes noise, and computes hashes.
6. **Classification & Extraction**: Classifier evaluates authority (Law, Regulatory Guidance, Industry Standard, Vendor Info). `EvidenceService` parses verbatim sentences and builds a TF-IDF index.
7. **Scoring & Enrichment**: Governance Engine scores the use case deterministically, attaches retrieved evidence to corresponding dimensions, detects conflicts, and saves the report.
8. **Traceability**: All connections from Use Case → Query → Source → Evidence → Assessment are persisted in SQLite.
