# openzt-eval

Model evaluation tool for testing LLMs with braintrust and autoevals.

## Features
- Support for local models via lmstudio
- Support for remote models through OpenAI-compatible APIs
- Braintrust proxy support for unified access to multiple model providers
- Autoevals integration for advanced scoring
- Configurable test suites with expected outputs
- Async evaluation with detailed metrics

## Setup

1. Copy `.env.example` to `.env` and configure your API keys:
```bash
cp .env.example .env
```

2. Set up your API keys:
- For OpenAI: Set `OPENAI_API_KEY`
- For Braintrust proxy: Set `BRAINTRUST_API_KEY`
- For local models: Ensure lmstudio server is running

## Usage

### Basic Usage

```bash
# Evaluate a local model
openzt-eval --models local:local:http://localhost:1234

# Evaluate OpenAI model
openzt-eval --models gpt4:openai::gpt-4

# Use Braintrust proxy for multiple models
export BRAINTRUST_API_KEY=your-key
openzt-eval --models \
  gpt4:custom:https://api.braintrust.dev/v1/proxy:gpt-4 \
  claude:custom:https://api.braintrust.dev/v1/proxy:claude-3-opus
```

### Model Specification Format

`name:type[:endpoint][:model_id][:api_key]`

- `name`: Identifier for the model in results
- `type`: One of `local`, `openai`, `anthropic`, `gemini`, `custom`
- `endpoint`: (Optional) API endpoint URL
- `model_id`: (Optional) Model identifier for the API
- `api_key`: (Optional) API key if not set in environment

### Test Cases

Create a JSON file with test cases:
```json
[
  {
    "name": "math_test",
    "prompt": "What is 2 + 2?",
    "expected": "4",
    "metadata": {"category": "math"}
  }
]
```

Run with custom tests:
```bash
openzt-eval --models model:type --test-file tests.json
```

### Options

- `--test-file`: JSON file with test cases
- `--output`: Save results to JSON file
- `--project`: Braintrust project name
- `--no-braintrust`: Disable Braintrust integration
- `--no-autoevals`: Disable autoevals scorers
- `--check-length`: Add length validation
- `--verbose`: Enable detailed logging