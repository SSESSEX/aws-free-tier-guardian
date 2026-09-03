# Architecture

AWS Free-Tier Guardian is a read-only AWS governance scanner built with Python, boto3, PostgreSQL, Docker, Kubernetes, and GitHub Actions.

## High-Level Architecture

```mermaid
flowchart TD
    A[AWS Account] --> B[boto3 Scanner Modules]

    B --> C[S3 Scanner]
    B --> D[EC2 Scanner]
    B --> E[EBS Scanner]
    B --> F[Elastic IP Scanner]
    B --> G[Security Group Scanner]
    B --> H[CloudWatch Logs Scanner]
    B --> I[IAM Access Key Scanner]
    B --> J[CloudTrail Scanner]
    B --> K[RDS Scanner]
    B --> BA[AWS Budgets Scanner]

    C --> L[Rule Evaluation Engine]
    D --> L
    E --> L
    F --> L
    G --> L
    H --> L
    I --> L
    J --> L
    K --> L
    BA --> L

    L --> M[Service-Level Summaries]
    M --> N[Global Summary Builder]

    N --> O[JSON Scan Report]
    N --> P[Markdown Executive Report]
    N --> Q[PostgreSQL Persistence]

    O --> Y[Snapshot Adapter]
    Y --> Z[Timestamped JSON Snapshots]
    Z --> AA[Deterministic Diff Engine]
    AA --> AB[Markdown Diff Report]
    AA --> AC[Structured JSON Change Events]
    AB --> AD[Count-Based File Retention]
    AC --> AD

    Q --> R[scan_runs]
    Q --> S[resources]
    Q --> T[findings]

    U[Docker Compose] --> B
    V[Kubernetes CronJob] --> B
    W[GitHub Actions] --> X[Pytest Test Suite]
```

## Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant Runner as Scanner Runner
    participant AWS as AWS APIs
    participant Rules as Rule Engine
    participant Reports as Report Writers
    participant Snapshots as Snapshot Pipeline
    participant DB as PostgreSQL

    User->>Runner: Run scanner
    Runner->>AWS: Read AWS resource metadata
    AWS-->>Runner: Return service data
    Runner->>Rules: Evaluate service rules
    Rules-->>Runner: Return findings
    Runner->>Reports: Build JSON and Markdown reports
    Runner->>DB: Persist scan run, resources, and findings
    Runner->>Snapshots: Flatten and save timestamped state
    Snapshots->>Snapshots: Compare latest two snapshots
    Snapshots-->>Runner: Return Markdown and JSON diffs
    Runner->>Snapshots: Apply optional file-count retention
    Runner-->>User: Print summary and top risks
```

## Data Model

```mermaid
erDiagram
    scan_runs ||--o{ resources : contains
    resources ||--o{ findings : has

    scan_runs {
        int id
        timestamp scan_time
        string aws_profile
        string aws_region
        timestamp created_at
    }

    resources {
        int id
        int scan_run_id
        string service
        string resource_type
        string resource_id
        string region
        jsonb raw_json
    }

    findings {
        int id
        int resource_id
        string check_name
        string status
        string severity
        string message
    }
```

## Design Principles

* Read-only AWS access
* Least-privilege IAM policies
* Service-specific scanner modules
* Service-specific rule modules
* Normalized PostgreSQL persistence
* JSONB storage for raw AWS resource metadata
* Human-readable Markdown reporting
* Versioned, machine-readable JSON change events
* Opt-in, count-based snapshot retention
* Unit-tested rule evaluation
* Redacted public example reports
* Docker and Kubernetes execution support
