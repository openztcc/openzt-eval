#!/usr/bin/env python3
"""Example of using the RustBuildScorer to evaluate LLM code generation."""

import asyncio
import json
import logging
from openzt_eval.models import ModelLoader, ModelConfig
from openzt_eval.evaluator import Evaluator, EvalCase
from openzt_eval.scorers import RustBuildScorer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_cases():
    """Create example test cases for Rust code generation."""
    
    # Example 1: Simple function implementation
    test_case_1 = EvalCase(
        name="implement_fibonacci",
        prompt="""
Implement a Rust function that calculates the nth Fibonacci number iteratively.
The function should have the signature: `fn fibonacci(n: u32) -> u64`

Requirements:
- Handle the base cases (n=0 returns 0, n=1 returns 1)
- Use an iterative approach for efficiency
- Return type should be u64 to handle larger numbers
""",
        expected=json.dumps({
            "repo_url": "https://github.com/rust-lang/rust",  # Example repo - replace with actual test repo
            "tag_or_branch": "master",
            "file_path": "src/lib.rs",
            "replacement_target": "// TODO: Implement fibonacci function",
            "description": "Fibonacci function implementation test"
        }),
        metadata={
            "category": "algorithms",
            "difficulty": "easy",
            "expected_errors": 0,
            "expected_warnings": 0
        }
    )
    
    # Example 2: Struct with methods
    test_case_2 = EvalCase(
        name="implement_stack",
        prompt="""
Complete the implementation of a generic Stack data structure in Rust.

```rust
struct Stack<T> {
    items: Vec<T>,
}

impl<T> Stack<T> {
    fn new() -> Self {
        // TODO: Implement new
    }
    
    fn push(&mut self, item: T) {
        // TODO: Implement push
    }
    
    fn pop(&mut self) -> Option<T> {
        // TODO: Implement pop
    }
    
    fn is_empty(&self) -> bool {
        // TODO: Implement is_empty
    }
}
```

The implementation should:
- Create a new empty stack
- Allow pushing items onto the stack
- Allow popping items from the stack (returning None if empty)
- Check if the stack is empty
""",
        expected=json.dumps({
            "repo_url": "https://github.com/rust-lang/rust",
            "tag_or_branch": "master", 
            "file_path": "src/stack.rs",
            "replacement_target": "// TODO: Implement all stack methods",
            "description": "Generic stack implementation test"
        }),
        metadata={
            "category": "data_structures",
            "difficulty": "medium",
            "expected_errors": 0,
            "expected_warnings": 0
        }
    )
    
    # Example 3: Error handling and Result types
    test_case_3 = EvalCase(
        name="implement_division",
        prompt="""
Implement a safe integer division function in Rust that handles division by zero.

```rust
fn safe_divide(dividend: i32, divisor: i32) -> Result<i32, String> {
    // TODO: Implement safe division with proper error handling
}
```

Requirements:
- Return Ok(result) for successful division
- Return Err with a descriptive message for division by zero
- Handle integer overflow appropriately
""",
        expected=json.dumps({
            "repo_url": "https://github.com/rust-lang/rust",
            "tag_or_branch": "master",
            "file_path": "src/math.rs", 
            "replacement_target": "// TODO: Implement safe_divide function",
            "description": "Safe division with error handling"
        }),
        metadata={
            "category": "error_handling",
            "difficulty": "medium",
            "expected_errors": 0,
            "expected_warnings": 0
        }
    )
    
    return [test_case_1, test_case_2, test_case_3]


async def main():
    """Run the Rust build evaluation example."""
    logger.info("Starting Rust Build Scorer example")
    
    # Set up a test model (you would configure this with your actual model)
    model_configs = [
        ModelConfig(
            name="test_model",
            model_type="openai", 
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4",
            wrap_openai=False  # Set to True for braintrust proxy
        )
    ]
    
    # Create model loader
    model_loader = ModelLoader(model_configs)
    await model_loader.load_models()
    
    # Create scorers
    # RustBuildScorer with custom configuration
    rust_scorer = RustBuildScorer(
        use_clippy=True,           # Run clippy checks
        allow_warnings=True,       # Allow warnings but penalize them
        error_penalty=1.0,         # Full penalty for each error
        warning_penalty=0.1,       # 10% penalty for each warning
        clippy_penalty=0.05,       # 5% penalty for each clippy lint
        timeout=300                # 5-minute timeout for builds
    )
    
    # Stricter scorer for production code
    strict_rust_scorer = RustBuildScorer(
        use_clippy=True,
        allow_warnings=False,      # Fail on any warnings
        error_penalty=1.0,
        warning_penalty=0.5,       # Higher penalty for warnings
        clippy_penalty=0.1,        # Higher penalty for clippy issues
        timeout=180
    )
    
    # Create evaluator with the Rust build scorer
    evaluator = Evaluator(
        model_loader=model_loader,
        scorers=[rust_scorer],     # You can also add: strict_rust_scorer
        use_braintrust=False,      # Set to True if you want braintrust logging
        project_name="rust-code-eval",
        use_autoevals=False        # Disable autoevals for this example
    )
    
    # Create test cases
    test_cases = create_test_cases()
    
    # Note: These test cases use placeholder repository URLs
    # In a real scenario, you would:
    # 1. Create or use existing Rust repositories with TODO placeholders
    # 2. Ensure the repositories have the correct file structure
    # 3. Make sure the replacement targets exist in the files
    
    logger.info(f"Created {len(test_cases)} test cases")
    for case in test_cases:
        logger.info(f"  - {case.name}: {case.metadata.get('category', 'unknown')} "
                   f"({case.metadata.get('difficulty', 'unknown')})")
    
    try:
        # Run evaluation
        logger.info("Starting evaluation...")
        results = await evaluator.evaluate(test_cases, model_names=["test_model"])
        
        # Print results
        evaluator.print_summary(results)
        
        # Detailed results
        print("\n" + "="*60)
        print("DETAILED RESULTS")
        print("="*60)
        
        for result in results:
            print(f"\nModel: {result.model_name}")
            print(f"Case: {result.case_name}")
            print(f"Passed: {'✅ YES' if result.passed else '❌ NO'}")
            print(f"Average Score: {result.average_score:.3f}")
            print(f"Duration: {result.duration_ms:.1f}ms")
            
            for scorer_name, score_result in result.scores.items():
                print(f"  {scorer_name}:")
                print(f"    Score: {score_result.score:.3f}")
                print(f"    Passed: {'✅' if score_result.passed else '❌'}")
                print(f"    Reason: {score_result.reason}")
                
                if score_result.metadata:
                    # Print build details if available
                    if 'build_errors' in score_result.metadata:
                        print(f"    Build Errors: {score_result.metadata['build_errors']}")
                    if 'build_warnings' in score_result.metadata:
                        print(f"    Build Warnings: {score_result.metadata['build_warnings']}")
                    if 'clippy_lints' in score_result.metadata:
                        print(f"    Clippy Lints: {score_result.metadata['clippy_lints']}")
        
        # Save detailed results to JSON
        results_data = []
        for result in results:
            results_data.append({
                "model_name": result.model_name,
                "case_name": result.case_name,
                "passed": result.passed,
                "average_score": result.average_score,
                "duration_ms": result.duration_ms,
                "timestamp": result.timestamp.isoformat(),
                "scores": {
                    name: {
                        "score": score.score,
                        "passed": score.passed,
                        "reason": score.reason,
                        "metadata": score.metadata
                    }
                    for name, score in result.scores.items()
                },
                "response": result.response[:500] + "..." if len(result.response) > 500 else result.response
            })
        
        with open("rust_eval_results.json", "w") as f:
            json.dump(results_data, f, indent=2, default=str)
        
        logger.info("Results saved to rust_eval_results.json")
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())