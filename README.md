# Veridia v1

**A versioned, causality-aware memory architecture for systems where knowledge changes.**

---

Veridia is a memory architecture designed for language model systems that must track how facts evolve over time. It stores knowledge as explicit, ordered state transitions rather than as documents or embedding vectors. This structural difference enables retrieval that respects *when* something was true and *why* it changed.

---

Most retrieval-augmented systems treat knowledge as a static collection. Documents are chunked, embedded, and retrieved by semantic similarity. When information updates, new documents enter the index alongside old ones. The retrieval layer has no built-in understanding that one document supersedes another. Queries return results based on topical relevance, not temporal validity.

This creates a class of failure that matters in specific domains. A compliance audit asks what policy was in effect on a particular date. A legal research query requires the version of a regulation before an amendment. A technical investigation traces when a configuration parameter changed and what triggered the update. In each case, the system must guarantee that all retrieved facts were simultaneously true at the queried point in time. Semantic similarity alone cannot provide this guarantee.

Veridia addresses this by making versioning structural rather than cosmetic. Instead of annotating documents with timestamps and hoping retrieval ranks them correctly, Veridia records the causal transition between knowledge states as its fundamental unit of storage. A document enters the system, is converted into one or more of these transitions, and may then be discarded. Queries resolve against a reconstructed state at a specific version, not against a set of possibly contradictory chunks.

The project is in active development as an MVP (Minimum Viable Product). This README describes the architecture, the concepts it rests on, and the tradeoffs it makes.

---

## Contents

- [The Problem](#the-problem)
- [Design Philosophy](#design-philosophy)
- [Core Concepts](#core-concepts)
- [High-Level Architecture](#high-level-architecture)
- [Simple Example](#simple-example)
- [Architectural Principles](#architectural-principles)
- [Advantages](#advantages)
- [Limitations](#limitations)
- [Benchmarks](#benchmarks)
- [Repository Structure](#repository-structure)
- [Roadmap](#roadmap)
- [Citation](#citation)
- [License](#license)

---

The next section defines the problem in detail: what happens when retrieval systems encounter evolving knowledge, and why existing mitigations leave fundamental gaps.