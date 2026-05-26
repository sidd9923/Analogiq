# Analogiq

**Cross-domain scientific idea retrieval via analogical matchmaking.**

Analogiq is a backend search engine that helps researchers discover analogous ideas across disciplinary boundaries — connecting a problem in *neuroscience* to a structurally similar solution from *materials science*, for example. Rather than keyword search, it uses **analogical similarity**: a fusion of semantic embeddings, structural text overlap, and relational predicate matching.

Presented at **ACM CHI '24** and adopted by research teams at the University of Maryland.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         REST API (Flask)                          │
│   POST /api/v1/search/query    POST /api/v1/graph/expand          │
│   POST /api/v1/search/index    POST /api/v1/graph/guides          │
└───────────────┬──────────────────────────┬───────────────────────┘
                │                          │
    ┌───────────▼──────────┐   ┌──────────▼──────────────┐
    │    Search Pipeline   │   │   Social Proximity Graph  │
    │                      │   │                           │
    │  SentenceTransformer │   │  Semantic Scholar API     │
    │  ──────────────────  │   │  ─────────────────────── │
    │  FAISS IndexFlatIP   │   │  NetworkX DiGraph (BFS)  │
    │  (50K+ abstracts,    │   │  Shortest-path guide      │
    │   sub-200ms latency) │   │  finder (≤3 hops)         │
    │  ──────────────────  │   │  ─────────────────────── │
    │  Analogical re-rank  │   │  Ray parallel expansion   │
    │  (semantic + struct  │   │  (circle 1 → 2)           │
    │   + relational)      │   │                           │
    └───────────┬──────────┘   └──────────┬────────────────┘
                │                          │
    ┌───────────▼──────────────────────────▼───────────────┐
    │          Ray Worker Pool  (parallel batch tasks)      │
    └───────────────────────────────────────────────────────┘
                │
    ┌───────────▼──────────────────────────────────────────┐
    │   SQLite / PostgreSQL (SQLAlchemy ORM)                │
    │   FAISS index + metadata  (persisted to disk)         │
    │   Graph store (NetworkX pickles / Neo4j-ready)        │
    └──────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Detail |
|---|---|
| **Analogical search** | Ensemble of semantic (60%), structural TF-IDF (25%), and relational SVO (15%) signals |
| **FAISS ANN index** | `IndexFlatIP` (cosine) with IVF auto-upgrade above 100K vectors; sub-200ms p99 |
| **Distributed encoding** | Sentence-Transformers batches parallelised via Ray remote tasks |
| **Social proximity** | Co-authorship graph expanded to depth-2 using Ray parallel Semantic Scholar calls |
| **Guide finder** | BFS shortest-path (NetworkX) from a seeker to candidate guides within ≤ 3 hops |
| **REST API** | Flask blueprints, typed request validation, structured JSON errors |
| **Production-ready** | Docker multi-stage build, Kubernetes manifests, gunicorn with gthread workers |
| **SQL persistence** | SQLAlchemy ORM; seekers, social circles, and guide paths stored in `seekers` / `guide_paths` tables |

---

## Project Structure

```
analogiq/
├── app/
│   ├── api/
│   │   ├── search.py          # POST /search/query, /search/index
│   │   ├── graph.py           # POST /graph/expand, /graph/guides
│   │   └── health.py          # GET  /health
│   ├── core/
│   │   ├── faiss_index.py     # Build / persist / query FAISS index
│   │   ├── similarity.py      # Semantic, structural, relational algorithms
│   │   ├── models.py          # Domain dataclasses (Paper, SeekerProfile …)
│   │   └── exceptions.py      # Custom exception hierarchy
│   ├── db/
│   │   ├── models.py          # SQLAlchemy ORM tables
│   │   ├── session.py         # Session factory + context manager
│   │   └── repositories.py    # SeekerRepository, GraphRepository
│   └── services/
│       ├── search_service.py  # Orchestrates encode → FAISS → re-rank
│       └── graph_service.py   # Seeker info, graph expansion, guide-finder
├── config/
│   └── settings.py            # Env-based config (dev / prod / test)
├── deploy/
│   ├── docker/
│   │   ├── Dockerfile         # Multi-stage build
│   │   └── docker-compose.yml # Local dev stack
│   └── k8s/
│       └── deployment.yaml    # Deployment + Service + PVC
├── scripts/
│   └── seed_index.py          # Seed FAISS from JSON or generate dummy data
├── tests/
│   ├── unit/
│   │   └── test_similarity.py # Similarity algorithm unit tests
│   └── integration/
│       └── test_search_api.py # Flask test-client integration tests
├── .env.example
├── requirements.txt
└── wsgi.py
```

> **Data policy:** All actual research abstracts and author graphs are excluded from this repository for IP and privacy reasons. Use the seed script to generate synthetic data for local testing (see [Quick Start](#quick-start)).

---

## API Reference

### Search

#### `POST /api/v1/search/query`
Retrieve the top-K analogically similar abstracts for a research problem.

```json
// Request
{
  "query": "self-repairing materials inspired by biological wound healing",
  "top_k": 10,
  "domain": "materials"   // optional filter
}

// Response
{
  "results": [
    {
      "id": "s2_12345",
      "title": "Autonomic healing in polymer networks via reversible bonds",
      "abstract": "...",
      "domain": "materials",
      "authors": ["Alice Lee", "Bob Kim"],
      "score": 0.8743,
      "rank": 1
    }
  ],
  "latency_ms": 142.6
}
```

#### `POST /api/v1/search/index`
Index a batch of documents. Triggers Ray-parallel encoding + FAISS build.

```json
// Request
{
  "documents": [
    { "id": "doc_001", "title": "...", "abstract": "...", "domain": "biology" }
  ]
}

// Response  201
{ "indexed": 1 }
```

### Graph

#### `GET /api/v1/graph/seeker/<seeker_id>`
Return cached author profile (Semantic Scholar ID). Fetches from API on miss.

#### `POST /api/v1/graph/expand`
Kick off async graph expansion for a seeker. Returns a `job_id` to poll.

```json
// Request
{ "seeker_id": 2112355103, "circle_level": 2, "batch_size": 10 }

// Response  202
{ "job_id": "a1b2c3...", "status": "queued" }
```

#### `GET /api/v1/graph/job/<job_id>`
Poll an expansion job. Final state includes `nodes` and `edges` count.

#### `POST /api/v1/graph/guides`
Find shortest co-authorship paths from a seeker to guide authors.

```json
// Request
{ "seeker_id": 2112355103, "guide_ids": [1823860, 144358729], "max_hops": 3 }

// Response
{
  "guides": [
    { "guide_id": 1823860, "path": [2112355103, 1739819976, 1823860], "path_length": 2 }
  ]
}
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker (optional)

### Local setup

```bash
git clone https://github.com/sidd9923/analogiq.git
cd analogiq

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # review and adjust if needed

# Seed a synthetic 500-doc index (no real data required)
python scripts/seed_index.py --generate-dummy 500

# Start the dev server
FLASK_ENV=development python wsgi.py
```

Test the search endpoint:

```bash
curl -s -X POST http://localhost:5000/api/v1/search/query \
  -H "Content-Type: application/json" \
  -d '{"query": "error correction in biological neural circuits", "top_k": 5}' | python -m json.tool
```

### Docker

```bash
docker compose -f deploy/docker/docker-compose.yml up --build
```

### Kubernetes

```bash
kubectl create namespace analogiq
kubectl apply -f deploy/k8s/deployment.yaml
```

---

## Algorithms

### Analogical Score (Ensemble)

Three signals are computed per candidate and combined as a weighted sum:

| Signal | Weight | Implementation |
|---|---|---|
| **Semantic** | 0.60 | Cosine similarity over [SPECTER](https://huggingface.co/allenai/specter) embeddings |
| **Structural** | 0.25 | TF-IDF cosine over unigram/bigram abstract profiles |
| **Relational** | 0.15 | Jaccard over heuristically extracted SVO triples |

Weights are configurable via environment variables (`ANALOGY_WEIGHT_*`).

### FAISS Index

- **Small corpora (< 100K docs):** `IndexFlatIP` — exact cosine search, no training required.
- **Large corpora (≥ 100K docs):** `IndexIVFFlat` — approximate search with configurable `nprobe` for the latency/recall trade-off.

Both cases normalise vectors with `faiss.normalize_L2` so inner product == cosine similarity.

### Social Proximity Graph

1. **Circle 1** — direct co-authors extracted from a seeker's Semantic Scholar paper list.
2. **Circle 2** — co-authors of co-authors, fetched in parallel batches via `ray.remote` tasks.
3. **Guide finder** — BFS shortest path (NetworkX `shortest_path`) from seeker to target guide; paths longer than `max_hops` are discarded.

---

## Running Tests

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Performance

| Metric | Value |
|---|---|
| Query latency (p99) | < 200 ms (50K index, SPECTER embeddings, M1 Pro) |
| Index throughput | ~400 docs/sec (Ray 4 workers, batch_size=64) |
| Graph expansion (circle 2) | ~15 min for 2K first-degree co-authors (API rate-limited) |

---

## Tech Stack

`Python` · `Flask` · `SQLAlchemy` · `FAISS` · `sentence-transformers` · `Ray` · `NetworkX` · `Docker` · `Kubernetes`

---

## Citation

> Shankar, S. et al. "Analogiq: Accelerating Cross-Domain Scientific Discovery Through Analogical Matchmaking." *ACM CHI 2024 Workshop on Human-AI Collaboration in Research.*

---

## License

MIT — see [LICENSE](LICENSE).
