# cargo-orchestrator

A Python library for running `cargo build` commands and parsing the resulting errors and warnings.

## Features

- Run cargo build with various configuration options
- Run cargo clippy for linting analysis
- Parse both JSON and human-readable output formats
- Support for release/debug builds, nightly toolchain, custom targets
- Extract and structure error messages, warnings, and their locations
- Easy-to-use Python API

## Installation

```bash
pip install cargo-orchestrator
```

## Usage

### Python API - Basic Example

```python
from cargo_orchestrator import CargoBuilder

# Create a builder instance
builder = CargoBuilder()

# Run cargo build
result = builder.build()

if result.success:
    print("Build successful!")
else:
    print(f"Build failed with {len(result.messages)} messages")
    
    # Print errors and warnings
    for msg in result.messages:
        if msg.level.value in ["error", "warning"]:
            print(f"{msg.level.value}: {msg.message}")
            for span in msg.spans:
                print(f"  --> {span.file_name}:{span.line_start}:{span.column_start}")
```

### Advanced Configuration

```python
from pathlib import Path
from cargo_orchestrator import CargoBuilder
from cargo_orchestrator.builder import BuildProfile

# Configure the builder
builder = CargoBuilder(
    root_dir=Path("/path/to/rust/project"),
    manifest_path=Path("/path/to/Cargo.toml"),
    target="x86_64-unknown-linux-gnu",
    profile=BuildProfile.RELEASE,
    use_nightly=True
)

# Build with specific features
result = builder.build(
    features=["async", "serde"],
    no_default_features=True,
    package="my-crate",
    use_clippy=False  # Set to True for clippy
)
```

### Running Clippy

Run cargo clippy for linting:

```python
# Run clippy with default settings
result = builder.clippy()

# Run clippy with specific configuration
result = builder.clippy(
    features=["async"],
    all_features=False,
    workspace=True
)

# Check for clippy-specific warnings
clippy_warnings = [m for m in result.messages if "clippy::" in (m.code or "")]
for warning in clippy_warnings:
    print(f"Clippy: [{warning.code}] {warning.message}")
```

### Parsing Output

The library automatically parses cargo output when using JSON format (default). For human-readable output:

```python
# Use human-readable format
result = builder.build(message_format="human")

# Access parsed messages
for msg in result.messages:
    print(f"Level: {msg.level.value}")
    print(f"Message: {msg.message}")
    if msg.code:
        print(f"Error code: {msg.code}")
```

## API Reference

### CargoBuilder

Main class for configuring and running cargo build commands.

**Constructor Parameters:**
- `root_dir` (Path, optional): Root directory to run cargo in
- `manifest_path` (Path, optional): Path to Cargo.toml
- `target` (str, optional): Target triple (e.g., 'x86_64-unknown-linux-gnu')
- `profile` (BuildProfile): Build profile (DEBUG or RELEASE)
- `use_nightly` (bool): Whether to use nightly toolchain

**build() Parameters:**
- `features` (List[str], optional): Features to enable
- `all_features` (bool): Enable all features
- `no_default_features` (bool): Disable default features
- `package` (str, optional): Specific package to build
- `workspace` (bool): Build entire workspace
- `message_format` (str): Output format ('json' or 'human')
- `extra_args` (List[str], optional): Additional cargo arguments
- `use_clippy` (bool): Run cargo clippy instead of cargo build

**clippy() Parameters:**
- Same as `build()` parameters but runs clippy instead

### BuildResult

Result object containing:
- `success` (bool): Whether the build succeeded
- `messages` (List[BuildMessage]): Parsed error/warning messages
- `stdout` (str): Raw stdout output
- `stderr` (str): Raw stderr output
- `return_code` (int): Process return code

### BuildMessage

Parsed message containing:
- `level` (MessageLevel): ERROR, WARNING, NOTE, HELP, or INFO
- `message` (str): The message text
- `code` (str, optional): Error code (e.g., 'E0425')
- `spans` (List[CodeSpan]): Code locations
- `children` (List[BuildMessage]): Related sub-messages
- `rendered` (str, optional): Fully rendered message

### CargoOutputParser

Parser for cargo build output in both JSON and human-readable formats:

```python
from cargo_orchestrator.parser import CargoOutputParser

parser = CargoOutputParser()

# Parse JSON output
messages = parser.parse_json_output(json_output)

# Parse human-readable output
messages = parser.parse_human_output(stderr_output)
```

## Requirements

- Python 3.10+
- Rust/Cargo installed and available in PATH

## License

MIT