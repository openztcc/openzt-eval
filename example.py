#!/usr/bin/env python3
"""
Example usage of the cargo-orchestrator library.
"""

from pathlib import Path
from cargo_orchestrator import CargoBuilder, BuildResult, BuildMessage
from cargo_orchestrator.builder import BuildProfile
from cargo_orchestrator.parser import MessageLevel


def print_message(msg: BuildMessage, indent: int = 0):
    """Pretty print a build message."""
    prefix = "  " * indent
    level_symbols = {
        MessageLevel.ERROR: "❌",
        MessageLevel.WARNING: "⚠️ ",
        MessageLevel.NOTE: "📝",
        MessageLevel.HELP: "💡",
        MessageLevel.INFO: "ℹ️ ",
    }
    
    symbol = level_symbols.get(msg.level, "  ")
    print(f"{prefix}{symbol} {msg.level.value}: {msg.message}")
    
    if msg.code:
        print(f"{prefix}   Code: {msg.code}")
    
    for span in msg.spans:
        print(f"{prefix}   --> {span.file_name}:{span.line_start}:{span.column_start}")
    
    # Print children recursively
    for child in msg.children:
        print_message(child, indent + 1)


def main():
    print("=== Cargo Orchestrator Example ===\n")
    
    # Example 1: Basic build
    print("1. Basic debug build:")
    builder = CargoBuilder()
    result = builder.build()
    
    if result.success:
        print("✅ Build successful!")
    else:
        print(f"❌ Build failed with code {result.return_code}")
    
    print(f"   Found {len(result.messages)} messages")
    for msg in result.messages[:5]:  # Show first 5 messages
        print_message(msg, indent=1)
    
    # Example 2: Release build with specific target
    print("\n2. Release build with target:")
    builder = CargoBuilder(
        profile=BuildProfile.RELEASE,
        target="x86_64-unknown-linux-gnu"
    )
    result = builder.build()
    print(f"   Result: {'Success' if result.success else 'Failed'}")
    
    # Example 3: Nightly build with features
    print("\n3. Nightly build with features:")
    builder = CargoBuilder(
        use_nightly=True,
        profile=BuildProfile.RELEASE
    )
    result = builder.build(
        features=["async", "experimental"],
        no_default_features=True
    )
    print(f"   Result: {'Success' if result.success else 'Failed'}")
    
    # Example 4: Build specific package in workspace
    print("\n4. Build specific package:")
    builder = CargoBuilder(
        manifest_path=Path("./Cargo.toml")
    )
    result = builder.build(package="my-crate")
    print(f"   Result: {'Success' if result.success else 'Failed'}")
    
    # Example 5: Parse human-readable output
    print("\n5. Human-readable output:")
    builder = CargoBuilder()
    result = builder.build(message_format="human")
    
    print(f"   Errors: {sum(1 for m in result.messages if m.level == MessageLevel.ERROR)}")
    print(f"   Warnings: {sum(1 for m in result.messages if m.level == MessageLevel.WARNING)}")
    
    # Show raw output sample
    if result.stderr:
        print("\n   Raw stderr (first 500 chars):")
        print(f"   {result.stderr[:500]}...")


if __name__ == "__main__":
    main()