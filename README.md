# mlflow-test-harness

Custom integration test harness for MLflow

## Overview

This test harness provides multi-layered testing capabilities for MLflow:
- **Unit tests**: Direct imports of MLflow API driven locally
- **Server tests**: Running MLflow as a server and hitting the API directly
- **Integration tests**: Full integration testing with test services and MLflow server

## Installation

### Prerequisites

- Python 3.10 or higher
- A local clone of the MLflow repository

### Installing the Test Harness

```bash
# Install the test harness with dev dependencies
pip install -e ".[dev]"
```

### Installing MLflow

This test harness requires MLflow to be installed as an editable dependency from a local repository. This allows you to test against your local MLflow changes.

**Using invoke (recommended):**

```bash
# Install MLflow from the default location (../mlflow)
invoke install-mlflow

# Install MLflow from a custom location
invoke install-mlflow --mlflow-path=/path/to/mlflow
```

**Manual installation:**

```bash
# Install MLflow from a local path
pip install -e /path/to/mlflow
```

### Uninstalling MLflow

```bash
# Using invoke
invoke uninstall-mlflow

# Or manually
pip uninstall mlflow
```

## Usage

### Running Tests

```bash
# Run all tests
invoke test

# Format code
invoke fmt

# Validate code quality
invoke validate
```

## Development

See [ROADMAP.md](ROADMAP.md) for the development plan and current progress.
