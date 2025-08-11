# cargo-orchestrator-cli

Command-line interface for cargo-orchestrator that provides a quick way to analyze cargo build output.

## Installation

```bash
pip install cargo-orchestrator-cli
```

Or install from the workspace:

```bash
uv sync
uv run cargo-orchestrator --help
```

## Usage

### Basic Usage

```bash
# Basic usage - build current directory
cargo-orchestrator

# Show only error and warning counts
cargo-orchestrator --quiet

# Build a specific project
cargo-orchestrator --root-dir /path/to/rust/project

# Release build with features
cargo-orchestrator --release --features async,serde

# Output as JSON
cargo-orchestrator --format json

# Show detailed output
cargo-orchestrator --verbose

# Run clippy instead of build
cargo-orchestrator --clippy

# Run clippy on a specific project
cargo-orchestrator --root-dir /path/to/project --clippy --quiet
```

### Options

- `--root-dir PATH`: Root directory for cargo to run in
- `--manifest-path PATH`: Path to Cargo.toml
- `--target TARGET`: Build for specific target triple
- `--release`: Build in release mode
- `--nightly`: Use nightly toolchain
- `--clippy`: Run cargo clippy instead of cargo build
- `--features FEATURES`: Comma-separated list of features
- `--all-features`: Enable all features
- `--no-default-features`: Disable default features
- `--package NAME`: Build specific package
- `--workspace`: Build entire workspace
- `--format {json,human,summary}`: Output format (default: summary)
- `--verbose/-v`: Show detailed output
- `--quiet/-q`: Only show error/warning counts

### Output Formats

#### Summary (Default)
Shows a colored, formatted summary with error/warning counts and details:

```
═══ Cargo Build Summary ═══

✓ Build succeeded

Statistics:
  • Errors:   0
  • Warnings: 3

Warnings:
  1. [unused_variables] unused variable: `x`
     → src/main.rs:10:9
```

#### JSON Format
Machine-readable output for integration with other tools:

```bash
cargo-orchestrator --format json | jq '.error_count'
```

#### Human Format
Raw cargo output as you would see it normally:

```bash
cargo-orchestrator --format human
```

### Examples

```bash
# Check a Rust project for errors
cargo-orchestrator --root-dir ~/my-project

# Run clippy on workspace with specific features
cargo-orchestrator --workspace --clippy --features async,serde

# Get machine-readable results
cargo-orchestrator --format json > build-results.json

# Quick error/warning count
cargo-orchestrator --quiet
# Output: Errors: 0, Warnings: 2

# Verbose output with full cargo details
cargo-orchestrator --verbose --format human

# Build for different target
cargo-orchestrator --target wasm32-unknown-unknown --release
```

### Integration with CI/CD

The CLI tool returns appropriate exit codes and can be used in CI/CD pipelines:

```bash
# Fails if build fails (non-zero exit code)
cargo-orchestrator --root-dir ./rust-project

# Only show counts in CI logs
cargo-orchestrator --quiet --root-dir ./rust-project

# Generate JSON report for further processing
cargo-orchestrator --format json --output build-report.json
```

### Using with uv

If you're working in the cargo-orchestrator workspace:

```bash
# Run directly with uv
uv run -m cargo_orchestrator_cli --help

# Or use the script
uv run cargo-orchestrator --root-dir ../some-project
```

## Requirements

- Python 3.10+
- Rust/Cargo installed and available in PATH
- cargo-orchestrator library (automatically installed as dependency)

## License

MIT