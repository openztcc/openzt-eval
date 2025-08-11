# CLAUDE.md - AI Assistant Context

This document provides context for AI assistants working on this workspace.

## Project Overview

This is a **uv workspace** containing tools for Rust development and model evaluation. The workspace uses Python 3.10+ and is managed with `uv` for dependency management.

## Workspace Structure

```
.
├── packages/                 # Library packages
│   └── cargo-orchestrator/   # Core library for cargo build/clippy parsing
├── apps/                     # Application packages
│   ├── cargo-orchestrator-cli/  # CLI for cargo-orchestrator
│   └── openzt-eval/          # Model evaluation tool
├── examples/                 # Example scripts
├── tests/                    # Workspace tests
├── test_projects/            # Test Rust projects for cargo-orchestrator
│   ├── error_project/        # Project with compilation errors
│   ├── warning_project/      # Project with warnings
│   ├── success_project/      # Successfully compiling project
│   └── clippy_project/       # Project with clippy warnings
└── test_data/                # Captured cargo outputs for testing
```

## Key Packages

### cargo-orchestrator (packages/cargo-orchestrator/)
- **Purpose**: Python library for running cargo build/clippy and parsing output
- **Key Classes**: `CargoBuilder`, `CargoOutputParser`, `BuildResult`, `BuildMessage`
- **Features**: JSON/human output parsing, error/warning extraction, clippy support
- **Testing**: Use test_projects/ for integration tests

### cargo-orchestrator-cli (apps/cargo-orchestrator-cli/)
- **Purpose**: CLI interface for cargo-orchestrator
- **Entry Point**: `cargo_orchestrator_cli.cli:main`
- **Output Formats**: summary (default), json, human
- **Key Features**: Colored output, quiet mode, CI/CD integration

### openzt-eval (apps/openzt-eval/)
- **Purpose**: Model evaluation using braintrust and autoevals
- **Model Support**: Local (lmstudio), Remote (OpenAI, Anthropic via braintrust proxy)
- **Key Classes**: `ModelLoader`, `Evaluator`, `EvalCase`
- **Scorers**: BasicResponseScorer, autoevals integration (Levenshtein)
- **Configuration**: Uses environment variables for API keys

## Development Guidelines

### Working with uv

```bash
# Sync workspace dependencies
uv sync

# Run CLI tools
uv run cargo-orchestrator --help
uv run -m openzt_eval --help

# Run tests
uv run python tests/run_tests.py

# Add new dependency to a package
cd apps/openzt-eval
uv add new-package
```

### Testing

1. **cargo-orchestrator**: Test with projects in `test_projects/`
2. **openzt-eval**: Use `--no-braintrust` flag for local testing without API keys
3. **Integration tests**: Run `uv run python tests/run_tests.py`

### Adding New Features

1. **New Package**: Add to appropriate directory (packages/ or apps/)
2. **Update pyproject.toml**: Add to workspace members
3. **Workspace Dependencies**: Use `tool.uv.sources` for internal dependencies
4. **Documentation**: Update package README and main workspace README

### Code Style

- Python 3.10+ type hints
- Docstrings for public APIs
- Error handling with proper logging
- Async/await for I/O operations (openzt-eval)

## Environment Variables

### For openzt-eval
- `OPENAI_API_KEY`: OpenAI API access
- `BRAINTRUST_API_KEY`: Braintrust proxy access
- `BRAINTRUST_API_URL`: Custom proxy endpoint (default: https://api.braintrust.dev/v1/proxy)

## Common Tasks

### Running Cargo Build Analysis
```bash
# Analyze current directory
uv run cargo-orchestrator

# Analyze specific project with clippy
uv run cargo-orchestrator --root-dir /path/to/rust/project --clippy

# Get JSON output for CI
uv run cargo-orchestrator --format json --quiet
```

### Running Model Evaluations
```bash
# Test with local model
uv run -m openzt_eval --models local:local:http://localhost:1234

# Test with multiple models via Braintrust proxy
export BRAINTRUST_API_KEY=your-key
uv run -m openzt_eval --models gpt4:custom:https://api.braintrust.dev/v1/proxy:gpt-4

# Test without external APIs
uv run -m openzt_eval --models test:openai --no-braintrust --no-autoevals
```

### Testing Changes
```bash
# Test cargo-orchestrator
uv run python tests/run_tests.py

# Test specific functionality
uv run python -c "from cargo_orchestrator import CargoBuilder; print(CargoBuilder())"

# Test CLI output
uv run cargo-orchestrator --root-dir test_projects/error_project --quiet
```

## Architecture Decisions

1. **uv Workspace**: Chosen for modern Python dependency management and workspace support
2. **Separate CLI Package**: Allows library to be used without CLI dependencies
3. **Test Projects**: Real Rust projects for integration testing
4. **Braintrust Proxy**: Unified interface for multiple model providers
5. **Async Model Interface**: Supports concurrent model evaluation

## Known Issues & Limitations

1. **Remote Models**: Require API keys (OpenAI, Braintrust)
2. **Local Models**: Require lmstudio server running
3. **Cargo Dependency**: Rust/Cargo must be installed for cargo-orchestrator
4. **Python Version**: Requires Python 3.10+

## Future Improvements

- [ ] Add more autoevals scorers (ClosedQA, Battle, LLMClassifier)
- [ ] Support for more model providers
- [ ] Caching for cargo build results
- [ ] Parallel evaluation support
- [ ] Web UI for openzt-eval results

## Debugging Tips

1. **Import Errors**: Ensure `uv sync` has been run
2. **API Errors**: Check environment variables for API keys
3. **Cargo Errors**: Verify Rust/Cargo is in PATH
4. **Test Failures**: Check test_projects/ have been built

## Project Maintenance

- **Update Dependencies**: `uv lock --upgrade`
- **Clean Build**: `rm -rf target/` in test_projects
- **Reset Workspace**: `rm -rf .venv && uv sync`

---

*Last Updated: Current workspace state as of this conversation*
*Primary Use: Rust development tooling and LLM evaluation*