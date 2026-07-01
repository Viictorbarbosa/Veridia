# When Not to Use Veridia

Veridia is not intended to replace every retrieval or knowledge management system.

Its architecture is optimized for evolving, versioned knowledge with explicit causal relationships. If these characteristics are absent, simpler or alternative approaches are often more appropriate.

---

# Unsuitable Use Cases

## Static Knowledge Bases

If the knowledge rarely or never changes, Veridia provides little additional value.

Examples include:

- Dictionaries
- Mathematical constants
- Reference manuals with infrequent updates
- Fixed encyclopedic content

In these scenarios, traditional document storage or search systems are usually sufficient.

---

## Semantic Similarity Search

Veridia is not designed to retrieve documents based on semantic similarity.

Example questions include:

- "Find documents similar to this paragraph."
- "Find articles discussing topics related to climate change."
- "Retrieve papers similar to this research."

Vector databases and embedding-based retrieval systems are generally better suited for these tasks.

---

## General-Purpose Chatbots

Applications focused on conversational assistance without historical reasoning typically do not benefit from Veridia.

Examples include:

- Customer support chatbots
- Virtual assistants
- FAQ systems
- Personal productivity assistants

These systems usually require broad semantic retrieval rather than temporal reasoning.

---

## Recommendation Systems

Veridia is not intended for recommendation engines.

Examples include:

- Product recommendations
- Movie recommendations
- Music recommendations
- Personalized content feeds

These applications rely on ranking, user behavior, and predictive models rather than versioned knowledge.

---

## Real-Time Similarity Retrieval

Applications that prioritize approximate nearest-neighbor search should use specialized retrieval systems.

Examples include:

- Large-scale semantic search
- Image retrieval
- Document similarity search
- Vector search over embeddings

Veridia does not perform similarity ranking.

---

## Frequently Changing Unstructured Text

If documents cannot be decomposed into persistent knowledge atoms, extracting meaningful deltas becomes difficult.

Examples include:

- Creative writing
- News articles with loosely structured information
- Social media posts
- Informal conversations

These domains often lack stable identities that can evolve consistently across versions.

---

# Characteristics of Poor Veridia Use Cases

A problem is generally **not** a good fit for Veridia when most of the following are true.

| Characteristic | Importance |
|---------------|------------|
| Knowledge is mostly static | High |
| Historical reconstruction is unnecessary | High |
| Provenance is not required | High |
| Semantic similarity is the primary retrieval mechanism | High |
| Approximate search is acceptable | High |
| Version history has little or no value | High |
| Documents lack persistent knowledge atoms | High |

---

# Better Alternatives

| Requirement | Recommended Approach |
|------------|----------------------|
| Semantic document search | Embedding-based retrieval (Vector RAG) |
| Approximate nearest-neighbor search | Vector database |
| Recommendation systems | Recommender models |
| Static document search | Traditional search engine |
| Keyword-based retrieval | Full-text indexing |
| General conversational AI | Standard LLM with Retrieval-Augmented Generation (RAG) |

---

# Architectural Trade-Offs

Every architecture makes trade-offs.

Veridia prioritizes:

- Deterministic state reconstruction.
- Temporal consistency.
- Explicit provenance.
- Immutable knowledge evolution.
- Causal traceability.

It intentionally does **not** optimize for:

- Semantic similarity search.
- Approximate retrieval.
- Recommendation quality.
- Broad document discovery.
- Embedding-based ranking.

---

# Summary

Veridia should be chosen only when **knowledge evolution is central to the problem**.

If the application primarily requires semantic search, document discovery, recommendation, or conversational retrieval without historical reasoning, other architectures will generally provide a simpler and more appropriate solution.