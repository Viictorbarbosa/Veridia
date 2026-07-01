# Benchmark Datasets

**Version:** 1.0.0  
**Status:** In Development  
**Last Updated:** 2026-07-01  
**Depends On:** [README](./README.md), [methodology.md](./methodology.md)

---

## Purpose

This directory contains all benchmark datasets used to evaluate Veridia and baseline systems.

Each dataset is versioned, documented, and designed to test specific architectural claims. Datasets include explicit ground truth: for every version, the correct value of every knowledge atom is known. For every change, the causal trigger is known. This enables exact measurement of correctness metrics.

No benchmark result is valid unless the dataset it was measured against is specified, versioned, and available for reproduction.

---

## Dataset Design Philosophy

### Ground Truth First

Every dataset is built from ground truth, not the other way around. We define what facts are true at each version. We define what changes occur between versions and what causes them. The documents that represent those changes are generated from the ground truth. This ensures that correctness metrics measure actual correctness, not plausibility.

### Controlled Complexity

Datasets are designed with specific properties: number of atoms, number of versions, change frequency, causal trigger diversity, and document complexity. Each property is documented. This enables isolation of which factors affect system performance.

### Reproducible Generation

Synthetic datasets are generated programmatically from a configuration file and a random seed. Any researcher can regenerate the exact dataset used in a published result. Real-world datasets include preprocessing scripts that transform raw sources into the standard benchmark format.

### Documented Limitations

Every dataset documents what it represents and what it does not represent. No dataset captures all aspects of real-world knowledge evolution. Results measured on one dataset do not necessarily generalize to others.

---


### metadata.json

```json
{
  "dataset_name": "small-policy",
  "dataset_version": "1.0.0",
  "created": "2026-07-01T00:00:00Z",
  "type": "synthetic",
  "domain": "policy_management",
  "parameters": {
    "num_atoms": 20,
    "num_versions": 10,
    "change_probability": 0.3,
    "causal_trigger_types": 5,
    "avg_deltas_per_document": 3.0
  },
  "generation": {
    "script": "benchmarks/datasets/synthetic/generate.py",
    "config": "benchmarks/datasets/synthetic/configs/small-policy.yaml",
    "seed": 42
  }
}
```

###atoms.json
 
```json
{
  "atoms": [
    {
      "atom_id": "data_retention_period_days",
      "domain": "compliance",
      "type": "integer",
      "description": "Number of days user data is retained"
    },
    {
      "atom_id": "max_connection_timeout_ms",
      "domain": "infrastructure",
      "type": "integer",
      "description": "Maximum connection timeout in milliseconds"
    }
  ]
}
```
###states.json
 
```json
{
  "versions": [
    {
      "version_tag": "v1.0",
      "timestamp": "2025-01-15T00:00:00Z",
      "atoms": {
        "data_retention_period_days": 90,
        "max_connection_timeout_ms": 30000
      }
    },
    {
      "version_tag": "v2.0",
      "timestamp": "2025-06-01T00:00:00Z",
      "atoms": {
        "data_retention_period_days": 30,
        "max_connection_timeout_ms": 5000
      }
    }
  ]
}
```

###trajectories.json

```json
{
  "atoms": [
    {
      "atom_id": "data_retention_period_days",
      "transitions": [
        {
          "version_tag": "v1.0",
          "operation": "SET",
          "value": 90,
          "previous_value": null,
          "cause": {
            "type": "INITIAL_INGESTION",
            "source_id": "policy-initial-v1",
            "timestamp": "2025-01-15T00:00:00Z",
            "description": "Initial policy publication"
          }
        },
        {
          "version_tag": "v2.0",
          "operation": "SET",
          "value": 30,
          "previous_value": 90,
          "cause": {
            "type": "DOCUMENT_UPDATE",
            "source_id": "policy-update-v2",
            "timestamp": "2025-06-01T00:00:00Z",
            "description": "Compliance review reduced retention period"
          }
        }
      ]
    }
  ]
}
```

# Synthetic Datasets

Synthetic datasets are programmatically generated corpora with known ground truth. They are the primary mechanism for measuring correctness metrics during development because every state transition, causal relationship, and expected output is fully controlled and reproducible.

---

## Design Parameters

Every synthetic dataset is defined by a configuration file specifying the parameters below.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `num_atoms` | Number of distinct knowledge atoms in the dataset | 20 |
| `num_versions` | Number of versions in the timeline | 10 |
| `change_probability` | Probability that a given atom changes value between adjacent versions | 0.30 |
| `causal_trigger_types` | Number of distinct causal event categories | 5 |
| `avg_deltas_per_document` | Average number of deltas produced per ingested document | 3.0 |
| `domain` | Knowledge domain simulated by the dataset | `policy_management` |
| `seed` | Random seed for deterministic dataset generation | 42 |

---

# Available Synthetic Datasets

## Small Policy Dataset

| Property | Value |
|----------|-------|
| Purpose | Rapid development iteration and correctness testing |
| Atoms | 20 |
| Versions | 10 |
| Change Probability | 0.30 |
| Causal Trigger Types | 5 |
| Average Deltas per Document | 3.0 |
| Domain | Policy management |
| Approximate Total Deltas | 60 |
| Total Documents | 10 |
| Execution Time (Development Hardware) | < 5 seconds |

### What it tests

- Temporal consistency at a scale where manual verification is practical.
- Reconstruction determinism across multiple versions.
- Trajectory completeness for atoms with relatively few modifications.
- Basic provenance accuracy.

### What it does **not** test

- Large-scale performance.
- High-frequency knowledge evolution.
- Complex interactions involving many atoms.

---

## Medium Policy Dataset

| Property | Value |
|----------|-------|
| Purpose | Measure scaling behavior |
| Atoms | 100 |
| Versions | 50 |
| Change Probability | 0.30 |
| Causal Trigger Types | 10 |
| Average Deltas per Document | 5.0 |
| Domain | Policy management |
| Approximate Total Deltas | 1,500 |
| Total Documents | 50 |
| Execution Time (Development Hardware) | < 5 minutes |

### What it tests

- Reconstruction time scaling as the delta log grows.
- Trajectory resolution time as version count increases.
- Storage overhead per delta at moderate scale.
- Correctness under realistic version histories.

### What it does **not** test

- Production-scale workloads.
- Extremely high change frequencies.
- Complex real-world document structures.

---

## High Churn Dataset

| Property | Value |
|----------|-------|
| Purpose | Stress-test trajectory completeness and provenance accuracy |
| Atoms | 50 |
| Versions | 30 |
| Change Probability | 0.70 |
| Causal Trigger Types | 5 |
| Average Deltas per Document | 8.0 |
| Domain | Technical documentation |
| Approximate Total Deltas | 1,050 |
| Total Documents | 30 |
| Execution Time (Development Hardware) | < 3 minutes |

### What it tests

- Trajectory completeness when most atoms evolve frequently.
- Provenance accuracy under dense delta histories.
- Ingestion cost when documents generate many deltas.
- Correctness during rapid knowledge evolution.

### What it does **not** test

- Long periods of stability.
- Low-frequency, high-impact updates.
- Very large atom populations.

---

# Dataset Generation Process

Synthetic datasets are generated through five deterministic stages.

| Stage | Description | Output |
|--------|-------------|--------|
| 1 | Generate knowledge atoms with identifiers, domains, and metadata | `atoms.json` |
| 2 | Generate ground-truth truth states for every version | `states.json` |
| 3 | Derive trajectories describing every state transition | `trajectories.json` |
| 4 | Generate synthetic source documents representing each version | `documents/` |
| 5 | Generate benchmark queries and expected outputs | `queries/`, `expected/` |

---

# Generation Command

```bash
python benchmarks/datasets/synthetic/generate.py \
  --config benchmarks/datasets/synthetic/configs/[config-name].yaml \
  --seed [seed] \
  --output benchmarks/datasets/synthetic/generated/[dataset-name]/
```

---

# Configuration File Format

```yaml
# Example: small-policy.yaml

dataset:
  name: "small-policy"
  domain: "policy_management"
  description: "Small policy dataset for rapid development iteration"

atoms:
  count: 20
  domains:
    - compliance
    - infrastructure
    - legal
    - security
    - billing

versions:
  count: 10
  start_timestamp: "2025-01-15T00:00:00Z"
  interval_days: 30

evolution:
  change_probability: 0.3
  causal_trigger_types:
    - INITIAL_INGESTION
    - DOCUMENT_UPDATE
    - COMPLIANCE_REVIEW
    - CORRECTION
    - POLICY_AMENDMENT

documents:
  avg_deltas_per_document: 3.0
  min_sentences: 1
  max_sentences: 5
```

---

# Reproducibility

Synthetic datasets are fully reproducible.

Given the same configuration file and random seed, the generation process must always produce identical outputs. Published benchmark results therefore include both the configuration file and the seed used during generation.

This guarantees that independent researchers can recreate the exact dataset used for evaluation.

---

## Verification Procedure

```bash
# Generate the dataset
python benchmarks/datasets/synthetic/generate.py \
  --config benchmarks/datasets/synthetic/configs/small-policy.yaml \
  --seed 42 \
  --output /tmp/verification/

# Compare against the published dataset
diff -r \
  /tmp/verification/ \
  benchmarks/datasets/synthetic/generated/small-policy-v1.0.0/
```

If no differences are reported, the generated dataset is identical to the published reference dataset.

# Real-World Datasets

Real-world datasets are collected from domains where knowledge naturally evolves over time. Unlike synthetic datasets, their ground truth is established through human annotation rather than programmatic generation.

These datasets complement synthetic benchmarks by evaluating Veridia under realistic conditions, including ambiguous language, inconsistent formatting, incomplete metadata, and complex document evolution.

---

## Acquisition

Real-world datasets are **not stored directly in this repository** because of licensing restrictions, copyright limitations, or repository size constraints.

Each dataset includes a `sources.md` file describing how to obtain the original data.

| Field | Description |
|--------|-------------|
| Dataset Name | Human-readable dataset identifier |
| Description | Summary of the dataset and its domain |
| Source | Original source or provider |
| License | Usage and redistribution terms |
| Snapshot Date | Exact version or acquisition date used |
| Size | Approximate document count and version count |

---

## Planned Real-World Datasets

| Dataset | Domain | Status | Ground Truth |
|---------|--------|--------|--------------|
| Policy Corpus | Government policies with amendments | Planned | Partial (in progress) |
| Technical Documentation | Open-source software documentation with version history | Planned | Not started |
| Regulatory Filings | Public regulatory submissions with tracked revisions | Candidate | Not started |

---

## Dataset Objectives

Real-world datasets evaluate Veridia under conditions that synthetic benchmarks cannot reproduce.

They focus on:

- Long-term document evolution.
- Natural language ambiguity.
- Multiple independent authors.
- Irregular update frequencies.
- Inconsistent document formatting.
- Partial or missing metadata.
- Complex causal histories.

---

## Preprocessing Pipeline

Every dataset is transformed into a standardized benchmark format before evaluation.

| Step | Description | Output |
|------|-------------|--------|
| 1. Document Extraction | Extract raw documents from PDFs, HTML, databases, or archives | Raw document collection |
| 2. Version Alignment | Associate documents with version identifiers or publication dates | Version timeline |
| 3. Atom Extraction | Identify or annotate persistent knowledge atoms | Atom definitions |
| 4. State Annotation | Build ground-truth truth states for every version | Ground-truth states |
| 5. Trajectory Annotation | Record causal transitions for each atom | Delta trajectories |
| 6. Query Generation | Produce benchmark queries and expected answers | Query suite |

---

## Preprocessing Command

```bash
python benchmarks/datasets/real-world/preprocess/prepare_[dataset-name].py \
    --input [path-to-raw-dataset] \
    --output benchmarks/datasets/real-world/processed/[dataset-name]/
```

---

## Ground Truth Annotation

Unlike synthetic datasets, ground truth is created through manual annotation.

Each dataset must document its annotation methodology.

| Aspect | Required Documentation |
|---------|------------------------|
| Annotators | Who performed the annotation |
| Guidelines | Annotation instructions |
| Agreement | Inter-annotator agreement (when applicable) |
| Resolution Process | How disagreements were resolved |
| Known Ambiguities | Difficult cases and their treatment |

---

## Ground Truth Levels

Not every dataset contains complete ground truth.

Datasets are classified according to annotation completeness.

| Ground Truth Level | Repository Label | Supported Metrics |
|--------------------|------------------|-------------------|
| Complete | — | All benchmark metrics |
| Partial | `partial-ground-truth` | Reconstruction Determinism, Ingestion Cost, Retrieval Latency |
| None | `no-ground-truth` | Performance and Cost metrics only |

---

## Dataset Requirements

Every real-world dataset should include:

- Original source reference.
- License information.
- Snapshot date.
- Version alignment methodology.
- Annotation methodology.
- Query definitions.
- Expected outputs (when available).
- Known limitations.

---

## Dataset Directory Structure

```text
real-world/
└── [dataset-name]/
    ├── README.md
    ├── sources.md
    ├── raw/
    ├── processed/
    ├── annotations/
    ├── queries/
    ├── expected/
    └── metadata.json
```

---

## Dataset README Template

Every real-world dataset should provide a README containing the following sections.

```markdown
# Dataset Name

## Overview

Short description of the dataset.

## Source

Dataset origin, acquisition method, license, and snapshot date.

## Statistics

| Property | Value |
|----------|-------|
| Documents | |
| Versions | |
| Knowledge Atoms | |
| Timespan | |

## Annotation Methodology

Describe how ground truth was created.

## Queries

Summary of available benchmark queries.

## Limitations

Known biases, missing information, and unsupported scenarios.

## Version History

| Version | Date | Changes |
|---------|------|----------|
| 1.0.0 | YYYY-MM-DD | Initial release |
```

---

## Current Status

| Dataset | Status | Ground Truth | Queries |
|---------|--------|--------------|---------|
| Policy Corpus | Planned | Partial | Not started |
| Technical Documentation | Planned | Not started | Not started |
| Regulatory Filings | Candidate | Not started | Not started |

---

## Limitations

Current real-world datasets have several practical constraints.

- Licensing restrictions may prevent redistribution.
- Manual annotation is time-consuming.
- Ground truth may be incomplete.
- Some domains lack explicit version metadata.
- Human annotation can introduce subjective interpretation.

These limitations are documented individually for each dataset.

---

## Relationship to Other Benchmark Documents

| Document | Purpose |
|----------|---------|
| `README.md` | Benchmark suite overview |
| `methodology.md` | Benchmark execution methodology |
| `metrics.md` | Metric definitions and computation |
| `reproducibility.md` | Benchmark reproduction guide |

---

## Revision History

| Version | Date | Changes |
|---------|------|----------|
| 1.0.0 | 2026-07-01 | Initial release |


# Query Design

Queries are the primary interface used to evaluate Veridia's retrieval capabilities. Each benchmark dataset includes a standardized set of queries designed to measure correctness, determinism, temporal consistency, and provenance accuracy.

Queries are divided into two categories that correspond to Veridia's two retrieval modes:

- **Semantic Memory Queries**, which retrieve the state of knowledge at a specific version.
- **Episodic Memory Queries**, which retrieve the trajectory of changes that produced a given state.

---

## Design Principles

Every benchmark query should satisfy the following principles.

| Principle | Description |
|-----------|-------------|
| Deterministic | The expected output is uniquely defined. |
| Version-aware | Every query targets an explicit or inferable version. |
| Reproducible | Running the same query on the same dataset always produces the same expected result. |
| Architecture-neutral | Queries evaluate behavior rather than implementation details. |
| Ground-truth validated | Every expected answer is verified against the dataset's ground truth. |

---

# Semantic Memory Queries

Semantic memory queries evaluate retrieval of facts from a reconstructed truth state without requiring historical explanations.

These queries measure whether Veridia can correctly reconstruct knowledge at a specific point in time.

## Query Types

| Query Type | Description | Example |
|------------|-------------|---------|
| Single Fact | Retrieve one knowledge atom | "What is the data retention period?" |
| Multi Fact | Retrieve multiple related atoms | "What are all compliance policies?" |
| Point-in-Time | Retrieve a fact at a historical version | "What was the retention period on May 1, 2025?" |
| Current State | Retrieve the latest reconstructed state | "What are all current policies?" |

---

## What Semantic Queries Measure

- Temporal Precision
- State Reconstruction Correctness
- Retrieval Accuracy
- Deterministic Reconstruction

---

# Episodic Memory Queries

Episodic memory queries evaluate retrieval of trajectories rather than reconstructed states.

Instead of asking **what is true**, they ask **how knowledge evolved**.

## Query Types

| Query Type | Description | Example |
|------------|-------------|---------|
| Single Atom Trajectory | Complete history of one atom | "How has the retention period changed?" |
| Time-Bounded Trajectory | Changes within a time interval | "What changed between January and June 2025?" |
| Cause-Specific | Changes caused by a particular event | "Which changes resulted from compliance reviews?" |
| Cross-Version Comparison | Compare two truth states | "What changed between v1.0 and v2.0?" |

---

## What Episodic Queries Measure

- Trajectory Completeness
- Provenance Accuracy
- Temporal Ordering
- Causal Consistency

---

# Expected Output Format

Every benchmark query is accompanied by a deterministic expected output used for validation.

Example:

```json
{
  "query_id": "semantic_001",
  "query_text": "What is the data retention period?",
  "query_type": "semantic",
  "target_version": "current",
  "expected_atoms": [
    "data_retention_period_days"
  ],
  "expected_values": {
    "data_retention_period_days": 30
  }
}
```

---

# Query Metadata

Each query contains standardized metadata.

| Field | Description |
|--------|-------------|
| query_id | Unique query identifier |
| query_text | Natural language query |
| query_type | Semantic or Episodic |
| target_version | Requested version or state |
| expected_atoms | Expected knowledge atoms |
| expected_values | Expected reconstructed values |
| expected_provenance | Expected trajectory information (if applicable) |

---

# Query Validation

A benchmark query is considered successful when:

- The correct truth state is reconstructed.
- The expected atoms are retrieved.
- Retrieved values exactly match the ground truth.
- Provenance information is correct (episodic queries).
- The output is deterministic across repeated executions.

---

# Recommended Query Distribution

A balanced benchmark suite should include both semantic and episodic queries.

| Query Category | Recommended Proportion |
|----------------|-----------------------:|
| Semantic — Single Fact | 25% |
| Semantic — Multi Fact | 15% |
| Semantic — Point-in-Time | 20% |
| Semantic — Current State | 10% |
| Episodic — Single Atom Trajectory | 15% |
| Episodic — Time-Bounded | 5% |
| Episodic — Cause-Specific | 5% |
| Episodic — Cross-Version Comparison | 5% |

---

# Dataset Requirements

Every benchmark dataset should provide:

- A query set.
- Expected outputs.
- Ground-truth validation.
- Query metadata.
- Version compatibility information.

Datasets without expected outputs cannot be used for correctness evaluation.

---

# Relationship to Other Documents

| Document | Purpose |
|----------|---------|
| `README.md` | Benchmark suite overview |
| `methodology.md` | Evaluation procedure |
| `metrics.md` | Metric definitions |
| `datasets.md` | Dataset specifications |

---

# Revision History

| Version | Date | Changes |
|---------|------|----------|
| 1.0.0 | 2026-07-01 | Initial release |

# 4. Dataset Versioning

Dataset versioning ensures that benchmark results remain reproducible, comparable, and traceable over time. Every dataset published by Veridia follows a strict versioning policy.

---

## Version Format

Datasets use **Semantic Versioning (SemVer)** in the format:

```text
MAJOR.MINOR.PATCH
```

Each component has a specific meaning.

| Component | Meaning | Example |
|-----------|---------|---------|
| **MAJOR** | Ground truth changed in a way that invalidates comparison with previous versions | `2.0.0` |
| **MINOR** | New data added without modifying existing ground truth | `1.1.0` |
| **PATCH** | Documentation, metadata, or formatting corrections only | `1.0.1` |

---

## Version Increment Rules

| Change | Version Increment | Comparable to Previous Results |
|---------|-------------------|--------------------------------|
| Modify an existing atom value | Major | No |
| Modify a causal transition | Major | No |
| Modify expected query outputs | Major | No |
| Add new documents without changing existing data | Minor | Yes |
| Add new benchmark queries | Minor | Yes |
| Add additional historical versions | Minor | Yes |
| Correct README or comments | Patch | Yes |
| Correct metadata only | Patch | Yes |
| Rename files without changing content | Patch | Yes |

---

## Immutability Policy

Published datasets are immutable.

Once a dataset version is released:

- Existing files are never modified.
- Existing ground truth is never edited.
- Existing expected outputs are never replaced.
- Existing benchmark results remain permanently reproducible.

Any modification, regardless of size, requires publishing a new dataset version.

---

## Compatibility

Benchmark results are only valid when evaluated against the exact dataset version used during execution.

Every benchmark report must include:

- Dataset name
- Dataset version
- Configuration file (for synthetic datasets)
- Random seed (for synthetic datasets)
- Benchmark framework version

Example:

```text
Dataset:
small-policy

Version:
1.0.0

Seed:
42

Framework:
Veridia Benchmark Suite v1.0
```

---

## Compatibility Matrix

| Dataset Version | Comparable with 1.0.0 | Notes |
|-----------------|----------------------|-------|
| 1.0.0 | Yes | Initial release |
| 1.0.1 | Yes | Metadata corrections only |
| 1.1.0 | Partial | Existing benchmark results remain valid |
| 2.0.0 | No | Ground truth changed |

---

## Dataset Identification

Each published dataset should include a metadata file describing its identity.

Example:

```yaml
name: small-policy
version: 1.0.0
dataset_type: synthetic
domain: policy_management
seed: 42
generated_at: 2026-07-01
generator_version: 1.0.0
```

---

## Directory Layout

Each dataset version is stored in its own directory.

```text
datasets/
└── synthetic/
    └── generated/
        ├── small-policy-v1.0.0/
        ├── small-policy-v1.1.0/
        └── small-policy-v2.0.0/
```

Older versions remain available for benchmark reproduction.

---

## Version Validation

Before publishing a new dataset version, the following validation checks should be performed.

| Validation | Purpose |
|------------|---------|
| Schema validation | Ensure files follow the expected structure |
| Ground truth validation | Verify internal consistency |
| Query validation | Confirm expected outputs remain correct |
| Determinism validation | Ensure regeneration produces identical output |
| Documentation validation | Verify README and metadata are complete |

A dataset should only be released after all validation checks pass successfully.

---

## Best Practices

- Never overwrite an existing dataset version.
- Preserve previous versions indefinitely.
- Document every version change in the dataset README.
- Include the dataset version in every published benchmark result.
- Use semantic versioning consistently across all datasets.
- Keep configuration files under version control.
- Archive deprecated datasets rather than deleting them.

---

## Relationship to Benchmark Results

Every benchmark result must explicitly reference the dataset version used during evaluation.

Without dataset version information:

- Results cannot be reproduced.
- Performance comparisons become invalid.
- Historical benchmark records lose scientific value.

For this reason, dataset versioning is considered a mandatory component of the Veridia benchmarking methodology.