# Benchmark Methodology

**Version:** 1.0.0  
**Status:** In Development  
**Last Updated:** 2026-07-01  
**Depends On:** [README](./README.md), [metrics.md](./metrics.md)

---

## Purpose

This document defines the methodology for designing, executing, and interpreting benchmarks in the Veridia project. It exists to ensure that every published result is obtained through a documented, reproducible, and fair process.

This document does not define the metrics themselves — those are in [metrics.md](metrics.md). It defines how benchmarks are constructed, what constraints they operate under, how baselines are selected, and what caveats apply to any results published from this suite.

---

## Hardware Constraints and Scope

### Honest Disclosure

All benchmarks in this project are designed and executed under significant hardware constraints. The development environment consists of a single machine with limited CPU cores, no dedicated GPU, and modest RAM. There is no access to cloud compute clusters, distributed storage, or high-memory instances.

This constraint is not hidden. It is stated here explicitly so that readers can calibrate their expectations.

### What This Means for Benchmarks

Given these constraints, the benchmark suite does not measure:

- Absolute throughput under production load
- Scalability across millions of deltas
- Performance on GPU-accelerated hardware
- Distributed deployment characteristics
- Network-bound latency in multi-node configurations

These are legitimate questions. They are simply not answerable with the hardware available. Attempting to answer them with inadequate hardware would produce misleading results. We choose to measure what we can measure rigorously rather than pretend to measure what we cannot.

### What We Measure Instead

The benchmark suite focuses on metrics that can be evaluated with limited hardware and that are architecturally meaningful:

- **Algorithmic complexity.** How do operations scale as a function of delta count, atom count, and query complexity? Measured through empirical observation and confirmed against theoretical expectations.
- **Ingestion cost.** What computational resources are consumed when transforming a document into deltas? Measured in wall-clock time and operation counts.
- **Retrieval latency.** How long does it take to reconstruct a truth state or resolve a trajectory? Measured at increasing log sizes.
- **Temporal consistency.** Do queries at version v return only facts true at version v? Measured against ground truth.
- **Reconstruction determinism.** Does the same log always produce the same state? Verified through repeated reconstruction.
- **Trajectory completeness.** Are all known state transitions represented in the delta log? Measured against ground truth.
- **Provenance accuracy.** Are causal attributions correct? Measured against ground truth.

These metrics are evaluated at scales achievable on development hardware — typically hundreds to low thousands of deltas, dozens to hundreds of atoms. Results are reported with explicit scale boundaries.

---

## Benchmark Design Principles

### Principle 1: Falsifiability

Every benchmark must test a claim that can be false. A benchmark that always passes regardless of system behavior provides no information. Each benchmark states the architectural claim it tests, the condition under which the claim would be falsified, and the metric used to evaluate it.

### Principle 2: Ground Truth Dependency

Every correctness benchmark depends on explicit ground truth. Temporal consistency benchmarks compare retrieved states against a known-correct state at each version. Trajectory completeness benchmarks compare the delta log against a known-correct sequence of changes. Ground truth is not inferred from system behavior. It is specified independently before the benchmark runs.

### Principle 3: Scale Transparency

Every result is reported with the scale at which it was measured: number of deltas, number of atoms, number of versions, document count, and query count. Results at one scale do not imply results at another scale. Extrapolation beyond measured scales is explicitly labeled as speculative.

### Principle 4: Reproducibility

Every result is accompanied by the exact configuration, dataset version, and execution commands used to produce it. The [reproducibility.md](reproducibility.md) document provides step-by-step instructions for independent verification. Results that depend on non-deterministic components (such as LLM-based transformation) are reported with variance across multiple runs.

### Principle 5: Baseline Fairness

Baseline systems are configured to represent reasonable implementations of their respective architectures. We do not deliberately degrade baseline performance. We document configuration choices and their justifications. If a baseline performs poorly, we investigate whether the poor performance reflects the architecture or our implementation of it.

---

## Dataset Design

### Synthetic Datasets

Synthetic datasets are programmatically generated corpora with controlled properties. They serve as the primary benchmark data source during development and for measuring scaling behavior.

A synthetic dataset is defined by the following parameters:

| Parameter | Description | Example |
|---|---|---|
| Atom count | Number of distinct knowledge atoms | 50 atoms |
| Version count | Number of versions in the timeline | 20 versions |
| Change probability | Probability that a given atom changes between adjacent versions | 0.3 |
| Causal trigger count | Number of distinct causal event types | 5 trigger types |
| Document-to-delta ratio | Average number of deltas produced per ingested document | 3.0 |

Synthetic datasets are generated with known ground truth: for every version, the correct value of every atom is known. For every change, the causal trigger is known. This enables exact measurement of correctness metrics.

### Real-World Datasets

Real-world datasets are anonymized corpora from domains where versioned knowledge naturally occurs. Candidates include:

- Open-source software documentation with version histories
- Publicly available policy documents with amendments
- Scientific literature with replication studies and retractions
- Regulatory filings with tracked changes

Real-world datasets require ground truth annotation. The annotation process and inter-annotator agreement (if applicable) are documented with the dataset.

### Dataset Documentation

Every dataset includes a README specifying:

- Source and provenance
- Generation parameters (for synthetic datasets)
- Annotation methodology (for real-world datasets)
- Known limitations and biases
- Version history of the dataset itself

---

## Baseline Selection

### Baseline Systems

The benchmark suite includes three baseline systems representing different architectural approaches to retrieval with evolving knowledge.

#### Traditional RAG

A naive retrieval-augmented generation pipeline without version awareness. Documents are chunked, embedded, and stored in a vector index. Queries are embedded and matched by cosine similarity. Version metadata is not used during retrieval. This baseline represents the simplest possible approach and establishes a lower bound on temporal consistency.

#### Hybrid RAG with Metadata Filtering

A RAG pipeline augmented with version metadata filters. Documents are chunked and embedded as in the traditional approach, but chunks carry version tags. Queries can specify a version filter that restricts retrieval to chunks with version tags within a range. This baseline represents a common production mitigation for version mixing.

#### Knowledge Graph

A graph-based knowledge representation where facts are stored as nodes with properties. Versioning is implemented through temporal property annotations or graph versioning. Queries traverse the graph with temporal constraints. This baseline represents structured knowledge approaches distinct from both vector search and delta-based models.

### Baseline Configuration

Each baseline is configured to be a reasonable, non-strawman implementation. Configuration choices are documented and justified. Where a baseline has tunable parameters (chunk size, embedding model, similarity threshold, filter strategy), we report results for multiple configurations and identify the best-performing configuration for each metric.

### What We Do Not Compare Against

We do not compare against commercial systems, systems requiring hardware we do not have access to, or systems that cannot be configured to produce reproducible results. The absence of a comparison does not imply superiority or inferiority. It reflects the practical constraints of the benchmark environment.

---

## Execution Protocol

### Environment

All benchmarks are executed in a controlled environment with documented specifications:

- Hardware: CPU model, core count, RAM, storage type
- Software: Operating system, Python version, dependency versions (pinned)
- Configuration: Veridia version, baseline versions, embedding model versions (if applicable)

The exact environment is recorded with each result. The [reproducibility.md](reproducibility.md) document provides instructions for replicating the environment.

### Warm-Up and Repetition

Benchmarks that measure latency or throughput include:

- A warm-up phase to allow caches to stabilize (if applicable)
- Multiple repetitions with reported variance
- Explicit documentation of what is cached between repetitions

Benchmarks that measure correctness (temporal consistency, determinism, provenance accuracy) are executed once per configuration. The result is deterministic for Veridia components. For baselines with non-deterministic components, results are reported with variance across runs.

### Scale Progression

Benchmarks that measure scaling behavior are executed at increasing scales:

1. Small: 50 deltas, 20 atoms, 10 versions
2. Medium: 500 deltas, 100 atoms, 50 versions
3. Large: 5000 deltas, 500 atoms, 200 versions

"Large" is defined relative to available hardware, not relative to production systems. The largest scale at which a benchmark is executed is always reported. Claims are not extrapolated beyond measured scales.

---

## Reporting Standards

### What Every Result Includes

Every published benchmark result includes:

- The metric being measured and its definition (linked to [metrics.md](metrics.md))
- The dataset used (with version and configuration)
- The system configuration (Veridia or baseline, with version and parameters)
- The execution environment (hardware and software)
- The raw measurement values
- The number of repetitions and observed variance
- The scale at which the measurement was taken

### What Every Result Acknowledges

Every published benchmark result includes a limitations section acknowledging:

- Hardware constraints and their impact on result generalizability
- Scale limitations and what cannot be concluded at larger scales
- Dataset limitations (synthetic vs. real-world, domain specificity)
- Known confounding factors
- What the benchmark does not measure

### Prohibited Claims

The following claims are prohibited in benchmark reporting unless accompanied by extraordinary evidence:

- "Veridia outperforms X" without specifying the metric, dataset, and conditions
- Claims of superiority based on a single metric or dataset
- Extrapolation of results to scales not measured
- Generalizations from synthetic datasets to real-world performance
- Claims that favorable results on one benchmark imply favorable results in production

---

## Limitations of This Methodology

### Hardware Limitations

All results are produced on a single development machine. Performance characteristics observed on this hardware may not generalize to distributed deployments, GPU-accelerated environments, or production-scale workloads. Ingestion cost measurements reflect single-threaded processing. Retrieval latency measurements reflect in-memory or local-storage access patterns. Network overhead, concurrency effects, and distributed coordination costs are not captured.

### Scale Limitations

Results are measured at scales of hundreds to low thousands of deltas. Many production knowledge bases contain millions of documents. The scaling behavior observed at our measurement scales may not hold at production scales. Algorithmic complexity analysis provides theoretical bounds, but empirical validation at scale is absent.

### Dataset Limitations

Synthetic datasets, while controlled and ground-truth-annotated, may not capture the complexity of real-world knowledge evolution. Real-world datasets, when available, are domain-specific and may not generalize. No single dataset can represent all use cases for which Veridia might be considered.

### Baseline Limitations

Baseline implementations are built and configured by the Veridia team. Despite efforts at fairness, implementer bias is possible. Baseline results should be treated as indicative, not definitive. Independent baseline implementations and reproductions are welcomed.

### Scope Limitations

This benchmark suite measures properties relevant to Veridia's architectural claims. It does not measure general-purpose retrieval quality, user satisfaction, or production readiness. A system that performs well on these benchmarks may still be unsuitable for a specific production use case.

---

## Evolution of This Methodology

This methodology document is versioned. As hardware becomes available, as datasets grow, and as the system matures, the methodology will be updated. Changes will be documented in the revision history. Early results produced under significant hardware constraints will be clearly labeled as such and will not be retroactively presented as definitive.

---

## Relationship to Other Documents

| Document | Relationship |
|---|---|
| [README](./README.md) | Overview of the benchmark suite |
| [metrics.md](metrics.md) | Formal definitions of all metrics referenced here |
| [reproducibility.md](reproducibility.md) | Step-by-step instructions for reproducing results |
| [datasets/](./datasets/) | Benchmark datasets with ground truth |
| [baselines/](./baselines/) | Baseline system implementations and configurations |
| [results/](./results/) | Published results and analysis |

---

## Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-07-01 | Initial release |