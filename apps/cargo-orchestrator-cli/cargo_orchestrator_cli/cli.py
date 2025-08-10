#!/usr/bin/env python3
"""
Command-line interface for cargo-orchestrator.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from cargo_orchestrator.builder import CargoBuilder, BuildProfile
from cargo_orchestrator.parser import MessageLevel


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="cargo-orchestrator",
        description="Run cargo build and analyze errors/warnings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cargo-orchestrator                           # Build in current directory
  cargo-orchestrator --release                 # Release build
  cargo-orchestrator --target x86_64-pc-windows-gnu
  cargo-orchestrator --features async,serde --no-default-features
  cargo-orchestrator --manifest-path ../other/Cargo.toml
  cargo-orchestrator --nightly --all-features
        """
    )
    
    # Build configuration
    parser.add_argument(
        "--root-dir",
        type=Path,
        help="Root directory for cargo to run in (default: current directory)"
    )
    
    parser.add_argument(
        "--manifest-path",
        type=Path,
        help="Path to Cargo.toml file"
    )
    
    parser.add_argument(
        "--target",
        type=str,
        help="Build for the target triple"
    )
    
    parser.add_argument(
        "--release",
        action="store_true",
        help="Build in release mode"
    )
    
    parser.add_argument(
        "--nightly",
        action="store_true",
        help="Use nightly toolchain"
    )
    
    parser.add_argument(
        "--clippy",
        action="store_true",
        help="Run cargo clippy for linting instead of cargo build"
    )
    
    # Feature flags
    parser.add_argument(
        "--features",
        type=str,
        help="Comma-separated list of features to activate"
    )
    
    parser.add_argument(
        "--all-features",
        action="store_true",
        help="Activate all available features"
    )
    
    parser.add_argument(
        "--no-default-features",
        action="store_true",
        help="Do not activate default features"
    )
    
    # Package selection
    parser.add_argument(
        "--package", "-p",
        type=str,
        help="Package to build"
    )
    
    parser.add_argument(
        "--workspace",
        action="store_true",
        help="Build all packages in workspace"
    )
    
    # Output format
    parser.add_argument(
        "--format",
        choices=["json", "human", "summary"],
        default="summary",
        help="Output format (default: summary)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only show error/warning counts"
    )
    
    return parser.parse_args()


def format_location(spans) -> str:
    """Format code location from spans."""
    if not spans:
        return ""
    span = spans[0]
    return f"{span.file_name}:{span.line_start}:{span.column_start}"


def print_colored(text: str, color: str = None, bold: bool = False):
    """Print colored text to terminal."""
    colors = {
        "red": "\033[91m",
        "yellow": "\033[93m",
        "green": "\033[92m",
        "blue": "\033[94m",
        "reset": "\033[0m",
        "bold": "\033[1m"
    }
    
    output = ""
    if bold:
        output += colors["bold"]
    if color and color in colors:
        output += colors[color]
    output += text
    output += colors["reset"]
    
    print(output)


def print_summary(result, args):
    """Print build summary."""
    errors = [m for m in result.messages if m.level == MessageLevel.ERROR]
    warnings = [m for m in result.messages if m.level == MessageLevel.WARNING]
    notes = [m for m in result.messages if m.level == MessageLevel.NOTE]
    helps = [m for m in result.messages if m.level == MessageLevel.HELP]
    
    if args.quiet:
        # Quiet mode: just the counts
        print(f"Errors: {len(errors)}, Warnings: {len(warnings)}")
        return
    
    # Header
    tool_name = "Clippy" if args.clippy else "Build"
    print_colored(f"\n═══ Cargo {tool_name} Summary ═══\n", bold=True)
    
    # Status
    if result.success:
        status_msg = "✓ Clippy passed" if args.clippy else "✓ Build succeeded"
        print_colored(status_msg, "green", bold=True)
    else:
        status_msg = "✗ Clippy failed" if args.clippy else "✗ Build failed"
        print_colored(status_msg, "red", bold=True)
    
    # Statistics
    print(f"\nStatistics:")
    print(f"  • Errors:   {len(errors)}")
    print(f"  • Warnings: {len(warnings)}")
    if args.verbose:
        print(f"  • Notes:    {len(notes)}")
        print(f"  • Helps:    {len(helps)}")
    
    # Show errors
    if errors and not args.quiet:
        print_colored("\nErrors:", "red", bold=True)
        for i, error in enumerate(errors[:10], 1):  # Show first 10
            location = format_location(error.spans)
            if location:
                print(f"  {i}. [{error.code or 'ERROR'}] {error.message}")
                print(f"     → {location}")
            else:
                print(f"  {i}. [{error.code or 'ERROR'}] {error.message}")
        
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    
    # Show warnings
    if warnings and not args.quiet:
        print_colored("\nWarnings:", "yellow", bold=True)
        for i, warning in enumerate(warnings[:10], 1):  # Show first 10
            location = format_location(warning.spans)
            if location:
                print(f"  {i}. [{warning.code or 'WARN'}] {warning.message}")
                print(f"     → {location}")
            else:
                print(f"  {i}. [{warning.code or 'WARN'}] {warning.message}")
        
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more warnings")
    
    # Show full output in verbose mode
    if args.verbose and result.stderr:
        print_colored("\nFull cargo output:", bold=True)
        print("─" * 60)
        print(result.stderr[:2000])  # First 2000 chars
        if len(result.stderr) > 2000:
            print("... (truncated)")


def print_json_output(result):
    """Print results as JSON."""
    import json
    
    output = {
        "success": result.success,
        "return_code": result.return_code,
        "error_count": len([m for m in result.messages if m.level == MessageLevel.ERROR]),
        "warning_count": len([m for m in result.messages if m.level == MessageLevel.WARNING]),
        "messages": [
            {
                "level": msg.level.value,
                "message": msg.message,
                "code": msg.code,
                "file": msg.spans[0].file_name if msg.spans else None,
                "line": msg.spans[0].line_start if msg.spans else None,
                "column": msg.spans[0].column_start if msg.spans else None,
            }
            for msg in result.messages
        ]
    }
    
    print(json.dumps(output, indent=2))


def main():
    """Main entry point for CLI."""
    args = parse_arguments()
    
    # Create builder with configuration
    builder = CargoBuilder(
        root_dir=args.root_dir,
        manifest_path=args.manifest_path,
        target=args.target,
        profile=BuildProfile.RELEASE if args.release else BuildProfile.DEBUG,
        use_nightly=args.nightly
    )
    
    # Parse features
    features = None
    if args.features:
        features = [f.strip() for f in args.features.split(",")]
    
    # Run build or clippy
    try:
        result = builder.build(
            features=features,
            all_features=args.all_features,
            no_default_features=args.no_default_features,
            package=args.package,
            workspace=args.workspace,
            message_format="json" if args.format != "human" else "human",
            use_clippy=args.clippy
        )
    except Exception as e:
        command = "cargo clippy" if args.clippy else "cargo build"
        print_colored(f"Error running {command}: {e}", "red")
        sys.exit(1)
    
    # Display results based on format
    if args.format == "json":
        print_json_output(result)
    elif args.format == "human":
        # Just print raw cargo output
        print(result.stderr)
    else:
        # Default summary format
        print_summary(result, args)
    
    # Exit with cargo's return code
    sys.exit(result.return_code)


if __name__ == "__main__":
    main()
