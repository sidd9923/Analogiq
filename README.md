# Analogiq - A distributed Search Engine that enables cross-domain discovery through analogical matchmaking

## Background
This was a research project I was a part of during my graduate studies at the University of Maryland. It investigates how to develop an interactive search engine that allows scientists and inventors to discover and adapt ideas across disciplinary boundaries. The system is designed to match research problems through **analogical similarity** rather than traditional keyword-based matching. 

A significant problem to address is **social proximity** – linking researchers and seekers through a social network graph built upon **Semantic Scholar IDs**. This enables users to identify connections based on academic co-authorship and discover collaborators within the shortest path across disciplines.

## Value proposition
The product helps researchers:
- Discover collaborators and novel ideas outside their immediate academic circles.
- Build and rank a personalized network of potential guides or collaborators using co-authorship graphs, research embeddings, and expertise-aware relevance scoring.
- Leverage a scalable distributed architecture—powered by Celery, Kafka/Faust, and MLflow Gateway—for fast graph queries, real-time updates, and reliable analogical search.

## Step-by-Step Implementation:
1. Social Network Graph Search (Graph DB + GPU Acceleration)
Construct a co-authorship knowledge graph using Semantic Scholar Author IDs, store it in a Graph Database (Neo4j/ArangoDB), and compute researcher proximity using shortest-path queries, optionally accelerated with cuGraph for large-scale traversal.

2. Analogical Guide Retrieval & Ranking (Embeddings + Vector DB)
Generate text embeddings for problems, papers, and researchers and store them in a Vector Database (pgvector/Qdrant). Use an ANN index (Annoy/Faiss) to retrieve and rank top-K guides based on semantic similarity, expertise overlap, and graph-based proximity.

3. Distributed Task Execution (Ray/Celery Workers)
Offload heavy workloads—including ingestion from Semantic Scholar, graph expansion, embedding generation, and ranking refreshes—to Celery or Ray worker pools running inside containers for non-blocking, horizontally scalable computation.

4. Event-Driven Streaming Architecture (Kafka + Faust)
Emit domain events such as author_ingested, graph_updated, problem_created, and rankings_updated to Kafka. Use Faust agents to maintain real-time system state, trigger downstream computation, and orchestrate microservice interactions through an event-driven pipeline.

5. LLM Governance & Unification (MLflow Gateway + Multi-Provider Adapters)
All LLM calls—used for analogical explanations, guide summaries, and reasoning—flow through an MLflow Gateway or internal LLM Orchestrator that provides centralized model routing, prompt logging, audit trails, and interoperability with OpenAI, Anthropic, Vertex AI, and local LLMs.

### Online Inference
The platform supports real-time inference across all microservices:
- Graph search (GPU-accelerated optional) efficiently retrieves social proximity information.
- Vector DB + ANN enables low-latency analogical guide ranking (<200ms target).
- gRPC services and GraphQL resolvers unify results at the API gateway.

This ensures researchers receive fast, up-to-date analogical matches and collaboration opportunities, even over large research corpora.

## Constraints
- Creating the entire social network graph is very time-inducing so keep this process to a minimum
- maintain low latency (>200ms) during gudie ranking step
- **Actual Data is kept hidden for proprietary purposes**. Will be using dummy research data

## Metrics
Key performance metrics:
- **Search Accuracy**: Measure the relevance of research matches based on analogical similarity.
- **Guide Ranking Precision**: Evaluate the accuracy of the top 'K' guides/authors retrieved based on field expertise and published work.
- **System Scalability**: Performance of the system when handling large datasets of researchers and publications.
- **Inference Speed**: Time taken to retrieve ranked results using Annoy for large datasets.

## Feasibility
The project is feasible due to the following:
- Availability of **Semantic Scholar's API** for accessing comprehensive academic data.
- Existing libraries for **graph construction** (NetworkX) and **GPU-accelerated search algorithms** (cuGraph) that will ensure efficient performance.
- **Annoy** for fast, scalable indexing and querying of embeddings to rank guides efficiently.
- Modern MLOps tools like **Kubernetes, TensorFlow Serving**, and **Kubeflow** to support the scalable model pipeline.

## Future Scope
Expand reseources to allow efficient network graph formation
Integrate a fine-tuned open source LLM that can create the analogical matching for us


