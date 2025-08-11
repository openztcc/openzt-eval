# Cargo Orchestrator Workspace

A uv workspace containing tools for Rust development and model evaluation.

## Packages

### 📦 [packages/cargo-orchestrator](packages/cargo-orchestrator/)
A Python library for running `cargo build` and `cargo clippy` commands with structured output parsing.

**Features:**
- Run cargo build/clippy with various options
- Parse JSON and human-readable output
- Extract structured error and warning messages
- Support for nightly, custom targets, features

**Install:** `pip install cargo-orchestrator`

### 🖥️ [apps/cargo-orchestrator-cli](apps/cargo-orchestrator-cli/)
Command-line interface for the cargo-orchestrator library.

**Features:**
- Colored, formatted output summaries
- JSON export for CI/CD integration
- Quiet mode for scripts
- Clippy integration

**Install:** `pip install cargo-orchestrator-cli`

**Usage:** `cargo-orchestrator --root-dir /path/to/project --clippy`

### 🔬 [apps/openzt-eval](apps/openzt-eval/)
Model evaluation tool for testing language models using braintrust and autoevals.

**Features:**
- Local model support via lmstudio
- Remote model support via braintrust proxy
- Automated evaluation scoring
- Support for multiple model providers
- Rich reporting and metrics

**Install:** See package README

**Usage:** `openzt-eval --models gpt4:openai claude:anthropic --test-file tests.json`

## Workspace Structure

```
.
├── packages/           # Library packages
│   └── cargo-orchestrator/
├── apps/              # Application packages
│   ├── cargo-orchestrator-cli/
│   └── openzt-eval/
├── examples/          # Example scripts
├── tests/             # Workspace tests
└── test_projects/     # Test Rust projects
```

## Development

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for package management
- Rust/Cargo (for cargo-orchestrator)

### Setup

```bash
# Clone and setup workspace
git clone <repo>
cd cargo-orchestrator
uv sync

# Run examples
uv run python examples/example.py

# Run CLI tools
uv run cargo-orchestrator --help
uv run -m openzt_eval --help
```

### Testing

```bash
# Run cargo-orchestrator tests
uv run python tests/run_tests.py

# Test CLI tools
uv run cargo-orchestrator --root-dir test_projects/success_project
uv run -m openzt_eval --models test:openai --no-braintrust --quiet
```

### Adding New Packages

1. **Library package:** Add to `packages/`
2. **Application package:** Add to `apps/`
3. **Update workspace:** Add to `pyproject.toml` workspace members
4. **Dependencies:** Use `tool.uv.sources` for workspace dependencies

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for your changes
4. Ensure all tests pass: `uv run python tests/run_tests.py`
5. Submit a pull request