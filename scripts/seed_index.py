#!/usr/bin/env python3
"""
scripts/seed_index.py
---------------------
Seed the FAISS index from a JSON file of documents.

Usage:
    python scripts/seed_index.py --data docs/sample_abstracts.json

The JSON file must be a list of objects with at least these keys:
    id, title, abstract, domain
Optional: authors (list of strings)

Actual data is not included in this repository (IP protected).
Generate dummy data with:
    python scripts/seed_index.py --generate-dummy 500
"""

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


DOMAINS = ["biology", "materials", "physics", "chemistry", "computer_science", "neuroscience"]

DUMMY_TEMPLATES = [
    "We present a novel approach to {topic} using {method}, achieving {metric} improvement over baselines.",
    "This work investigates {topic} through the lens of {method}. Our experiments demonstrate {metric} gains.",
    "{method} applied to {topic} reveals unexpected structural properties with applications in {domain}.",
    "Large-scale analysis of {topic} datasets using {method} uncovers latent patterns relevant to {domain}.",
]

TOPICS = [
    "protein folding", "network topology", "quantum entanglement", "neural plasticity",
    "polymer self-assembly", "epidemic spreading", "crystal growth", "signal propagation",
    "swarm behaviour", "energy dissipation", "membrane permeability", "error correction",
]

METHODS = [
    "graph neural networks", "variational autoencoders", "Monte Carlo simulation",
    "transformer-based architectures", "topological data analysis", "Bayesian inference",
    "reinforcement learning", "spectral clustering", "contrastive learning",
]


def generate_dummy(n: int) -> list[dict]:
    docs = []
    for i in range(n):
        template = random.choice(DUMMY_TEMPLATES)
        abstract = template.format(
            topic=random.choice(TOPICS),
            method=random.choice(METHODS),
            metric=f"{random.randint(5, 40)}%",
            domain=random.choice(DOMAINS),
        )
        docs.append({
            "id": f"dummy_{i:05d}",
            "title": f"Study {i}: {random.choice(TOPICS).title()} via {random.choice(METHODS).title()}",
            "abstract": abstract,
            "domain": random.choice(DOMAINS),
            "authors": [f"Author {random.randint(1, 999)}", f"Author {random.randint(1, 999)}"],
        })
    return docs


def main():
    parser = argparse.ArgumentParser(description="Seed Analogiq FAISS index")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--data", help="Path to JSON document file")
    group.add_argument("--generate-dummy", type=int, metavar="N", help="Generate N dummy documents")
    args = parser.parse_args()

    if args.generate_dummy:
        docs = generate_dummy(args.generate_dummy)
        print(f"Generated {len(docs)} dummy documents")
    else:
        with open(args.data) as f:
            docs = json.load(f)
        print(f"Loaded {len(docs)} documents from {args.data}")

    # Use the Flask app context to initialise DB / services
    from app import create_app
    from app.services.search_service import SearchService

    app = create_app("development")
    with app.app_context():
        svc = SearchService()
        count = svc.index_documents(docs)
        print(f"✓ Indexed {count} documents into FAISS")


if __name__ == "__main__":
    main()
