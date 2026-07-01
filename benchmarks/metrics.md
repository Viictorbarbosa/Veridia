# Benchmark Metrics

**Version:** 1.0.0  
**Status:** In Development  
**Last Updated:** 2026-07-01  
**Depends On:** [README](./README.md), [methodology.md](./methodology.md)

---

## Purpose

This document defines every metric used in the Veridia benchmark suite. Each metric is defined formally, with a clear description of what it measures, how it is computed, what its range is, and what a good score looks like.

A metric that appears in a benchmark result must be defined in this document. No metric may be used without a definition. No definition may be changed without incrementing the document version.

---

## Metric Categories

Metrics are organized into four categories reflecting the architectural claims they test.

| Category | Claims Tested |
|---|---|
| Correctness | Temporal consistency, reconstruction determinism, trajectory completeness, provenance accuracy |
| Cost | Ingestion cost, transformation cost, storage overhead |
| Performance | Retrieval latency, reconstruction time, trajectory resolution time |
| Quality | Factual precision at version, cross-version comparison accuracy |

---

## Correctness Metrics

### Temporal Precision

**Definition:** The proportion of facts returned by a version-scoped query that were actually true at the queried version.

**Formula:**
```

Temporal Precision = |Retrieved Facts ∩ Ground Truth at v| / |Retrieved Facts|

```

**Range:** 0.0 to 1.0, where 1.0 indicates perfect temporal consistency.

**Measurement:** For each version v in a test dataset, execute a set of queries scoped to v. Compare each retrieved fact against the ground truth state at v. A fact is correct if its atom identifier and value match the ground truth exactly.

**Target:** 1.0. Any value below 1.0 indicates that the system returned facts from a version other than the one requested, or returned incorrect values for the requested version.

**What a low score means:** The system is mixing facts from different versions in the same query response, or the truth state at the requested version was incorrectly reconstructed.

---

### Temporal Recall

**Definition:** The proportion of ground truth facts at a version that were successfully retrieved by a version-scoped query.

**Formula:**
```

Temporal Recall = |Retrieved Facts ∩ Ground Truth at v| / |Ground Truth at v|

```

**Range:** 0.0 to 1.0, where 1.0 indicates that all facts true at version v were retrieved.

**Measurement:** For each version v, execute a query requesting all facts at v. Compare the retrieved set against the complete ground truth state at v. A ground truth fact is considered retrieved if it appears in the response with the correct value.

**Target:** 1.0. Any value below 1.0 indicates that facts known to be true at version v were missing from the response.

**What a low score means:** The delta log is incomplete — some state transitions present in the ground truth are not represented as deltas. Or the reconstruction process failed to apply some deltas.

---

### Reconstruction Determinism

**Definition:** A binary verification that reconstructing the same version from the same delta log always produces the same truth state.

**Formula:**
```

Reconstruction Determinism = 1.0 if S₁ = S₂ for two independent reconstructions, else 0.0

```

**Range:** 0.0 or 1.0. There is no partial credit. The reconstruction is either deterministic or it is not.

**Measurement:** For each version in the test dataset, reconstruct the truth state twice from the same delta log. Compare the two states byte-for-byte or field-for-field. If they differ, determinism is violated. Execute this test on different machines if available, or after system restart, to detect hidden non-determinism from system time, random seeds, or external state.

**Target:** 1.0. Any value below 1.0 indicates a fundamental violation of architectural principle P2.

**What a low score means:** The system has a non-deterministic component in its reconstruction path — possibly an LLM call, a timestamp injection, a random seed, or an unordered data structure. This is a critical failure.

---

### Trajectory Completeness

**Definition:** The proportion of state transitions in the ground truth that are represented as deltas in the delta log.

**Formula:**
```

Trajectory Completeness = |Transitions in Delta Log ∩ Ground Truth Transitions| / |Ground Truth Transitions|

```

**Range:** 0.0 to 1.0, where 1.0 indicates that every known state transition is recorded as a delta.

**Measurement:** For each atom, the ground truth specifies the sequence of values it held and the version at which each value change occurred. Compare this sequence against the deltas in the log that reference that atom. A transition matches if a delta exists with the correct atom identifier, version tag, and value change.

**Target:** 1.0. Values below 1.0 indicate missing deltas.

**What a low score means:** The ingestion pipeline failed to produce deltas for some documents, or the transformation stage did not detect some changes. Facts changed without the system recording the change.

---

### Provenance Accuracy

**Definition:** The proportion of retrieved facts whose causal attribution matches the ground truth.

**Formula:**
```

Provenance Accuracy = |Facts with correct cause| / |Retrieved facts with cause assertions|

```

**Range:** 0.0 to 1.0, where 1.0 indicates perfect causal attribution.

**Measurement:** For facts retrieved with provenance (episodic memory queries), compare the cause descriptor attached to the fact against the ground truth cause. A cause is correct if its type, source identifier, and description match the ground truth for that version transition.

**Target:** 1.0. Lower values indicate incorrect or missing causal attribution.

**What a low score means:** The system is attributing changes to wrong causes, fabricating causes, or failing to record causes at ingestion time.

---

### Version Resolution Accuracy

**Definition:** The proportion of temporally-qualified queries that resolve to the correct version tag.

**Formula:**
```

Version Resolution Accuracy = |Queries resolving to correct v| / |Total temporally-qualified queries|

```

**Range:** 0.0 to 1.0.

**Measurement:** For queries with temporal expressions ("on May 1, 2025," "as of Q2 2025"), compare the version tag the system resolved against the ground truth version tag for that temporal expression. The resolution is correct if the resolved version tag is the highest version tag with a causal timestamp not exceeding the query timestamp.

**Target:** 1.0. Lower values indicate that the time-to-version resolution logic is incorrect.

**What a low score means:** The system is mapping temporal expressions to wrong versions, causing queries to retrieve facts from the wrong point in time.

---

## Cost Metrics

### Ingestion Cost Per Document

**Definition:** The wall-clock time required to transform one document into deltas, measured from the moment the normalized document enters the transformation stage to the moment the resulting deltas are validated and ready for storage.

**Unit:** Seconds per document.

**Measurement:** Process a batch of documents of varying sizes and complexity. Measure the total transformation time and divide by the number of documents. Report mean, median, and 95th percentile. Report separately for documents that produce different numbers of deltas.

**What this captures:** The computational overhead of Veridia's ingestion model compared to chunking and embedding. Higher ingestion cost is an expected tradeoff for retrieval determinism and temporal consistency.

**Limitations:** Measured on development hardware without GPU acceleration. Absolute values will differ on production hardware. Relative comparisons between document sizes and complexity levels are more informative than absolute values.

---

### Transformation Cost Per Delta

**Definition:** The computational cost of producing one delta during document transformation, measured in LLM API calls or CPU cycles.

**Unit:** API calls per delta, or CPU-seconds per delta.

**Measurement:** Count the number of LLM inference calls made during transformation of a document batch. Divide by the number of deltas produced. Alternatively, measure CPU time consumed by deterministic parsers. Report for both LLM-based and deterministic transformation paths if both exist.

**What this captures:** The marginal cost of extracting each additional fact from a document. Helps estimate ingestion costs for documents of varying factual density.

**Limitations:** LLM API costs depend on provider pricing and model selection — factors outside Veridia's architecture. Reported in abstract units (calls per delta) rather than monetary cost.

---

### Storage Overhead Per Delta

**Definition:** The storage space consumed by one delta in the delta log, including all metadata, indexing structures, and serialization overhead.

**Unit:** Bytes per delta.

**Measurement:** Insert a known number of deltas into an empty delta log. Measure the total storage consumed. Divide by the number of deltas. Report separately for different storage backends if applicable.

**What this captures:** The storage cost of maintaining the full causal history versus storing only the current state. Veridia's append-only model consumes more storage than systems that overwrite old values. This metric quantifies that tradeoff.

**Limitations:** Storage overhead depends on serialization format, compression, and indexing — all implementation choices, not architectural constraints. Results reflect the reference implementation, not a theoretical minimum.

---

### Reconstruction Cost Per Version

**Definition:** The computational cost of reconstructing a truth state at a specific version, measured as a function of delta log size.

**Unit:** CPU-seconds or operation count.

**Measurement:** Reconstruct truth states at versions distributed across the log (early, middle, recent). Measure the time or operation count for each reconstruction. Report how reconstruction cost scales with the number of deltas applied.

**What this captures:** The retrieval-time cost of Veridia's model. State reconstruction replays deltas from the log. As the log grows, reconstruction cost grows unless caching or incremental reconstruction is used.

**Limitations:** Measured without caching optimizations that a production deployment would likely employ. Represents worst-case cold reconstruction cost.

---

## Performance Metrics

### Retrieval Latency

**Definition:** The wall-clock time from query submission to structured result delivery, excluding LLM synthesis time.

**Unit:** Milliseconds.

**Measurement:** Execute queries of different types (single-fact semantic, full-state semantic, single-atom trajectory, multi-atom trajectory). Measure the time from query interpretation completion to retrieval result availability. Report mean, median, and 95th percentile across query types and version positions.

**What this captures:** The responsiveness of the Veridia memory layer. Excludes LLM synthesis time to isolate the memory architecture's contribution to end-to-end latency.

**Limitations:** Measured on development hardware. Network latency for remote storage backends is not captured. Absolute values will differ in production.

---

### Trajectory Resolution Time

**Definition:** The wall-clock time to retrieve a complete trajectory for one atom across a specified version range.

**Unit:** Milliseconds.

**Measurement:** For atoms with varying numbers of modifications (1 change, 10 changes, 100 changes), measure the time to retrieve the full trajectory. Report how resolution time scales with trajectory length.

**What this captures:** The cost of episodic memory queries, which require scanning the delta log for all deltas matching a specific atom identifier.

**Limitations:** Depends on indexing structures for atom identifiers in the delta log. A naive full-scan implementation will show linear scaling. An indexed implementation will show sub-linear scaling. Both are implementation choices.

---

### State Reconstruction Scaling

**Definition:** How state reconstruction time grows as a function of delta log size.

**Unit:** Dimensionless scaling factor (e.g., "O(n)", "O(log n)").

**Measurement:** Measure reconstruction time at increasing log sizes. Fit the observed times to complexity classes. Report both the empirical scaling behavior and the theoretical complexity of the reconstruction algorithm.

**What this captures:** Whether Veridia's state reconstruction remains practical as the knowledge base grows. Linear scaling is expected for full-log replay. Sub-linear scaling is achievable with incremental reconstruction and caching.

**Limitations:** Measured at scales achievable on development hardware (hundreds to thousands of deltas). Scaling behavior observed at these sizes may not hold at production scales with millions of deltas.

---

## Quality Metrics

### Factual Precision at Version

**Definition:** The proportion of individual facts in a query response that are correct for the requested version.

**Formula:**
```

Factual Precision at v = |Correct facts in response| / |Total facts in response|

```

**Range:** 0.0 to 1.0.

**Measurement:** For each query, extract individual factual assertions from the response. Compare each assertion against the ground truth at the queried version. An assertion is correct if the atom identifier and value match exactly.

**What this captures:** End-to-end factual accuracy including both retrieval correctness and LLM synthesis fidelity. A correct fact retrieved from Veridia can still be misrepresented by the LLM in the final response.

**Limitations:** Requires factual extraction from natural language responses, which may introduce annotation subjectivity. Best measured on structured responses or with automated factual verification tools.

---

### Cross-Version Comparison Accuracy

**Definition:** The proportion of cross-version differences correctly identified in a comparison query response.

**Formula:**
```

Comparison Accuracy = |Correctly identified differences| / |Total actual differences between versions|

```

**Range:** 0.0 to 1.0.

**Measurement:** For queries asking "what changed between v_a and v_b?", compare the differences listed in the response against the ground truth diff between S(v_a) and S(v_b). A difference is correctly identified if the atom, old value, new value, and cause match the ground truth.

**What this captures:** The system's ability to synthesize multi-version comparisons accurately, which requires both correct retrieval from two versions and correct diff computation.

**Limitations:** Depends on LLM synthesis quality as well as retrieval correctness. A retrieval system can return perfect data and the LLM can still misrepresent the comparison.

---

## Metric Selection Guide

Different use cases prioritize different metrics. This guide maps use cases to the metrics that matter most.

| Use Case | Primary Metrics | Secondary Metrics |
|---|---|---|
| Compliance auditing | Temporal Precision, Temporal Recall | Provenance Accuracy, Version Resolution Accuracy |
| Incident investigation | Trajectory Completeness, Provenance Accuracy | Trajectory Resolution Time |
| Policy management | Factual Precision at Version, Cross-Version Comparison Accuracy | Reconstruction Determinism |
| Regulatory reporting | Temporal Precision, Provenance Accuracy | Retrieval Latency |
| Research synthesis | Trajectory Completeness, Cross-Version Comparison Accuracy | Factual Precision at Version |

---

## What These Metrics Do Not Capture

This document defines metrics that test Veridia's architectural claims. The following are explicitly not captured by these metrics:

- User satisfaction or perceived answer quality
- Factual accuracy of the LLM's synthesis beyond what was retrieved
- Robustness to adversarial queries
- Performance under concurrent query load
- Behavior under partial system failure
- Migration cost from existing systems
- Operational complexity compared to alternatives

These are legitimate evaluation dimensions. They are simply not what this benchmark suite measures. A system that scores perfectly on these metrics may still fail in production for reasons outside the scope of these benchmarks.

---

## Relationship to Other Documents

| Document | Relationship |
|---|---|
| [README](./README.md) | Overview of the benchmark suite |
| [methodology.md](methodology.md) | How benchmarks are designed and executed using these metrics |
| [reproducibility.md](reproducibility.md) | How to reproduce results that report these metrics |
| [03 — Architectural Principles](../../docs/architecture/03-principles.md) | The architectural guarantees these metrics test |

---

## Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-07-01 | Initial release |