# Benchmarks

**Version:** 1.0.0  
**Status:** In Development  
**Last Updated:** 2026-07-01

---

## Purpose

This directory contains the Veridia benchmark suite — the datasets, methodologies, baseline configurations, evaluation harnesses, and results used to measure the architecture's performance against its stated goals.

Benchmarks in Veridia serve a specific purpose: to verify that the architectural guarantees claimed in the documentation hold under measurement. They are not designed to compare Veridia against other systems in general-purpose retrieval tasks. They are designed to measure the properties that Veridia claims to provide — temporal consistency, deterministic reconstruction, causal traceability, and provenance accuracy.

---

## What We Measure

Veridia's architecture makes specific, falsifiable claims. The benchmark suite exists to test those claims.

| Claim | What We Measure |
|---|---|
| Temporal consistency | Do queries at version v return only facts true at version v? |
| Deterministic reconstruction | Does the same delta log always produce the same truth state? |
| Causal traceability | Can every fact be traced to the delta and cause that produced it? |
| Trajectory completeness | Are all state transitions in the ground truth represented in the delta log? |
| Provenance accuracy | Are causal attributions correct for retrieved facts? |

We do not measure semantic search quality, embedding accuracy, or retrieval recall in the traditional sense. Those metrics belong to a different class of system. Veridia's benchmarks measure correctness under knowledge evolution — a dimension that similarity-based retrieval benchmarks do not typically capture.

---