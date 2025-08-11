#!/usr/bin/env python3
"""CLI interface for openzt-eval."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List
import json

from rich.console import Console
from rich.logging import RichHandler

from .models import ModelLoader, ModelConfig, ModelType
from .evaluator import Evaluator, EvalCase
from .scorers import BasicResponseScorer, LengthScorer, ContainsScorer, RustBuildScorer

console = Console()


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )


def parse_model_spec(spec: str) -> ModelConfig:
    """Parse a model specification string.
    
    Format: name:type[:endpoint][:model_id][:api_key]
    Examples:
        - local_llama:local:http://localhost:1234:llama2
        - gpt4:openai::gpt-4
        - claude:anthropic::claude-3-opus
        - custom:custom:https://api.braintrust.dev/v1/proxy:my-model:sk-xxx
    
    For Braintrust proxy usage:
        Set BRAINTRUST_API_KEY environment variable
        Use endpoint: https://api.braintrust.dev/v1/proxy
    """
    parts = spec.split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid model spec: {spec}. Format: name:type[:endpoint][:model_id][:api_key]")
    
    name = parts[0]
    type_str = parts[1].lower()
    
    # Map type string to ModelType
    type_map = {
        "local": ModelType.LOCAL,
        "openai": ModelType.OPENAI,
        "anthropic": ModelType.ANTHROPIC,
        "gemini": ModelType.GEMINI,
        "custom": ModelType.CUSTOM,
    }
    
    if type_str not in type_map:
        raise ValueError(f"Unknown model type: {type_str}. Valid types: {list(type_map.keys())}")
    
    model_type = type_map[type_str]
    endpoint = parts[2] if len(parts) > 2 and parts[2] else None
    model_id = parts[3] if len(parts) > 3 and parts[3] else None
    api_key = parts[4] if len(parts) > 4 and parts[4] else None
    
    return ModelConfig(
        name=name,
        type=model_type,
        endpoint=endpoint,
        model_id=model_id,
        api_key=api_key
    )


def load_test_cases(file_path: Path) -> List[EvalCase]:
    """Load test cases from a JSON file."""
    with open(file_path) as f:
        data = json.load(f)
    
    cases = []
    for item in data:
        if isinstance(item, str):
            # Simple string prompt
            cases.append(EvalCase(
                name=f"case_{len(cases)+1}",
                prompt=item
            ))
        elif isinstance(item, dict):
            # Full case specification
            cases.append(EvalCase(
                name=item.get("name", f"case_{len(cases)+1}"),
                prompt=item["prompt"],
                expected=item.get("expected"),
                metadata=item.get("metadata")
            ))
        else:
            raise ValueError(f"Invalid test case format: {item}")
    
    return cases


def get_default_test_cases() -> List[EvalCase]:
    """Get default test cases for basic evaluation."""
    return [
        EvalCase(
            name="simple_greeting",
            prompt="Say hello in a friendly way.",
        ),
        EvalCase(
            name="basic_math",
            prompt="What is 2 + 2?",
            expected="4"
        ),
        EvalCase(
            name="explain_concept",
            prompt="Explain what machine learning is in one sentence."
        ),
        EvalCase(
            name="creative_writing",
            prompt="Write a haiku about programming."
        ),
        EvalCase(
            name="factual_question",
            prompt="What is the capital of France?",
            expected="Paris"
        ),
    ]


async def run_evaluation(args):
    """Run the evaluation."""
    # Parse model specifications
    model_configs = []
    for spec in args.models:
        try:
            config = parse_model_spec(spec)
            model_configs.append(config)
            console.print(f"[green]✓[/green] Parsed model: {config.name} (type: {config.type.value})")
        except ValueError as e:
            console.print(f"[red]✗[/red] Error parsing model spec '{spec}': {e}")
            return 1
    
    # Load models
    loader = ModelLoader()
    for config in model_configs:
        try:
            loader.load_model(config)
            console.print(f"[green]✓[/green] Loaded model: {config.name}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to load model {config.name}: {e}")
            if args.strict:
                return 1
    
    if not loader.models:
        console.print("[red]No models loaded successfully[/red]")
        return 1
    
    # Load test cases
    if args.test_file:
        try:
            cases = load_test_cases(Path(args.test_file))
            console.print(f"[green]✓[/green] Loaded {len(cases)} test cases from {args.test_file}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to load test cases: {e}")
            return 1
    else:
        cases = get_default_test_cases()
        console.print(f"[cyan]Using {len(cases)} default test cases[/cyan]")
    
    # Setup scorers
    scorers = [BasicResponseScorer(min_length=args.min_response_length)]
    if args.check_length:
        scorers.append(LengthScorer(min_length=10, max_length=1000))
    if args.rust_build:
        scorers.append(RustBuildScorer(
            use_clippy=args.rust_clippy,
            allow_warnings=not args.rust_strict,
            error_penalty=1.0,
            warning_penalty=0.1,
            clippy_penalty=0.05
        ))
    console.print(f"[cyan]Using {len(scorers)} scorer(s)[/cyan]")
    
    # Create evaluator
    evaluator = Evaluator(
        model_loader=loader,
        scorers=scorers,
        use_braintrust=not args.no_braintrust,
        project_name=args.project,
        use_autoevals=not args.no_autoevals
    )
    
    # Run evaluation
    console.print("\n[bold]Starting evaluation...[/bold]\n")
    results = await evaluator.evaluate(cases)
    
    # Print summary
    console.print("\n")
    evaluator.print_summary(results)
    
    # Save results if requested
    if args.output:
        output_data = []
        for result in results:
            output_data.append({
                "model": result.model_name,
                "case": result.case_name,
                "prompt": result.prompt,
                "response": result.response,
                "scores": {name: score.score for name, score in result.scores.items()},
                "passed": result.passed,
                "duration_ms": result.duration_ms,
                "timestamp": result.timestamp.isoformat()
            })
        
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        console.print(f"\n[green]✓[/green] Results saved to {args.output}")
    
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="openzt-eval",
        description="Evaluate language models using braintrust",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate a local model
  openzt-eval --models local_model:local:http://localhost:1234:llama2
  
  # Evaluate OpenAI model
  openzt-eval --models gpt4:openai::gpt-4
  
  # Use Braintrust proxy for multiple models
  export BRAINTRUST_API_KEY=your-key
  openzt-eval --models gpt4:custom:https://api.braintrust.dev/v1/proxy:gpt-4 \\
                       claude:custom:https://api.braintrust.dev/v1/proxy:claude-3-opus
  
  # Evaluate multiple models with different endpoints
  openzt-eval --models local:local gpt4:openai claude:anthropic
  
  # Use custom test cases
  openzt-eval --models local:local --test-file tests.json
  
  # Save results without Braintrust logging
  openzt-eval --models local:local --output results.json --no-braintrust
        """
    )
    
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="Model specifications (format: name:type[:endpoint][:model_id])"
    )
    
    parser.add_argument(
        "--test-file",
        help="JSON file containing test cases"
    )
    
    parser.add_argument(
        "--output",
        help="Save results to JSON file"
    )
    
    parser.add_argument(
        "--project",
        default="openzt-eval",
        help="Braintrust project name (default: openzt-eval)"
    )
    
    parser.add_argument(
        "--no-braintrust",
        action="store_true",
        help="Disable Braintrust integration"
    )
    
    parser.add_argument(
        "--no-autoevals",
        action="store_true",
        help="Disable autoevals scorers"
    )
    
    parser.add_argument(
        "--min-response-length",
        type=int,
        default=1,
        help="Minimum response length to pass basic scorer (default: 1)"
    )
    
    parser.add_argument(
        "--check-length",
        action="store_true",
        help="Add length scorer to check response lengths"
    )
    
    parser.add_argument(
        "--rust-build",
        action="store_true",
        help="Enable Rust build scorer for code generation evaluation"
    )
    
    parser.add_argument(
        "--rust-clippy",
        action="store_true",
        help="Enable clippy checks in Rust build scorer (requires --rust-build)"
    )
    
    parser.add_argument(
        "--rust-strict",
        action="store_true", 
        help="Fail Rust build scorer on warnings (requires --rust-build)"
    )
    
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit on first model loading error"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    try:
        sys.exit(asyncio.run(run_evaluation(args)))
    except KeyboardInterrupt:
        console.print("\n[yellow]Evaluation interrupted[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if args.verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()