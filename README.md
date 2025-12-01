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
- **Social Network Graph Search**: Build a GPU-accelerated co-authorship knowledge graph from Semantic Scholar IDs and compute researcher proximity using shortest-path queries.

- **Analogical Guide Ranking**: Generate embeddings for researchers and problems, and use ANN-based (Annoy) similarity search to retrieve and rank top-K guides by expertise, relevance, and proximity.

- **Distributed Task Execution (Celery)**: Offload heavy ingestion, graph expansion, embedding generation, and ranking workflows to Celery workers for scalable, non-blocking background processing.

- **Event-Driven Streaming (Kafka + Faust)**: Emit and consume system events (e.g., author_ingested, problem_created) via Kafka and process them with Faust agents to maintain real-time state and orchestrate downstream actions.

- **LLM Governance (MLflow Gateway)**: Route all analogical reasoning LLM calls through MLflow Gateway for centralized model routing, prompt/response logging, monitoring, and secure, auditable LLM inference.

## Inference
The system will support **online inference** to allow users to run search queries in real time. Both the **GPU-accelerated graph search** and **Annoy-based guide ranking** ensure that even with large datasets, queries are processed efficiently. Real-time processing is critical for providing up-to-date results to researchers.

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


