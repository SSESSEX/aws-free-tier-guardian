# ADR 001: Use Batch Automation Before Event-Driven Monitoring

## Status

Accepted

## Context

AWS Free-Tier Guardian is a read-only governance and cost-safety scanner.

The project currently collects AWS account configuration, evaluates deterministic rules, and produces structured findings. The next improvement is to make the scanner more operational by adding snapshot history, change detection, and scheduled execution.

There are two possible automation directions:

1. Scheduled batch scanning
2. Event-driven or streaming-style monitoring

Scheduled batch scanning means the system periodically asks:

> What does the AWS account look like now?

It then compares the latest result to previous results.

Event-driven monitoring means the system reacts when a specific cloud event occurs, such as a resource being created, deleted, or modified.

## Decision

AWS Free-Tier Guardian will use scheduled batch automation first.

The next architecture target is:

```text
AWS account configuration
        ↓
read-only boto3 collection
        ↓
timestamped JSON snapshot
        ↓
deterministic rule evaluation
        ↓
snapshot diff against previous run
        ↓
Markdown / JSON report
        ↓
optional PostgreSQL history
```

Event-driven monitoring is a future extension, not the immediate implementation path.

## Why Batch Comes First

Batch scanning is the better first implementation because the project is currently focused on:

- periodic governance checks;
- cost-safety visibility;
- explainable findings;
- deterministic rule evaluation;
- low operational complexity;
- local and CI-friendly execution;
- portfolio evidence that can be explained clearly in interviews.

The account does not currently require second-by-second detection of changes.

A daily or manually triggered scan is enough to prove the core engineering loop:

```text
collect → snapshot → compare → report → persist
```

## Why Streaming Is Not First

Streaming or event-driven monitoring would add more moving parts before the core snapshot and diff model is proven.

It may require services such as:

- event routing;
- configuration-change capture;
- alerting rules;
- dead-letter handling;
- more operational failure modes;
- additional IAM permissions;
- more complex testing.

Those are useful later, but adding them too early would make the project harder to reason about without improving the immediate value of the scanner.

## Trade-Offs

### Benefits of batch-first automation

- Simpler to build and test
- Easier to run locally
- Easier to explain in interviews
- Lower operational complexity
- Fits periodic governance and cost checks
- Provides a foundation for historical trend analysis
- Makes snapshot diffing straightforward

### Limitations

- Changes are only detected after the next scan
- Not suitable for urgent real-time incident response
- Does not immediately alert on every AWS API event
- May miss short-lived resources that appear and disappear between scans

## Future Extension

Event-driven monitoring can be added later if the project needs faster detection.

A future architecture could include:

```text
AWS event source
        ↓
event routing
        ↓
targeted resource re-scan
        ↓
rule evaluation
        ↓
alert or report
```

This should only be added after batch snapshots, diffing, and report history are working.

## Interview Explanation

The project deliberately starts with batch automation because cloud governance does not always require streaming complexity.

For this scanner, the first goal is to build a reliable monitoring loop that can repeatedly collect account state, compare it with previous state, and explain what changed.

Streaming would be useful for real-time incident response, but it would be premature before the snapshot and diff model is proven.

## Current Implementation Target

The next engineering task is:

```text
Add timestamped snapshot history and diff reporting.
```

This will make AWS Free-Tier Guardian more operational without overcomplicating the architecture.