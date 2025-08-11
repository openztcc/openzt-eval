#!/usr/bin/env python3
"""Simple test of the RustBuildScorer using a local test project."""

import asyncio
import json
import logging
from pathlib import Path
import tempfile
import shutil
from openzt_eval.scorers import RustBuildScorer, RustBuildTestCase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_repo():
    """Create a temporary test Rust project."""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    # Create Cargo.toml
    cargo_toml = '''[package]
name = "rust_eval_test"
version = "0.1.0"
edition = "2021"

[dependencies]
'''
    
    (repo_path / "Cargo.toml").write_text(cargo_toml)
    
    # Create src directory
    src_dir = repo_path / "src"
    src_dir.mkdir(exist_ok=True)
    
    # Create lib.rs with TODO placeholders
    lib_rs = '''pub fn fibonacci(n: u32) -> u64 {
    // TODO_FIBONACCI: Implement fibonacci function
    match n {
        0 => 0,
        1 => 1,
        _ => {
            let mut a = 0;
            let mut b = 1;
            for _ in 2..=n {
                let temp = a + b;
                a = b;
                b = temp;
            }
            b
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fibonacci() {
        assert_eq!(fibonacci(0), 0);
        assert_eq!(fibonacci(1), 1);
        assert_eq!(fibonacci(5), 5);
        assert_eq!(fibonacci(10), 55);
    }
}
'''
    
    (src_dir / "lib.rs").write_text(lib_rs)
    
    logger.info(f"Created test repo at: {repo_path}")
    return str(repo_path)


async def test_rust_build_scorer():
    """Test the RustBuildScorer with different code implementations."""
    
    # Create test repository
    repo_path = create_test_repo()
    
    try:
        # Test case 1: Good implementation
        logger.info("Testing with a correct implementation...")
        
        test_case = RustBuildTestCase(
            repo_url=f"file://{repo_path}",  # Local repository
            tag_or_branch="main",
            file_path="src/lib.rs",
            replacement_target="    // TODO_FIBONACCI: Implement fibonacci function",
            description="Fibonacci implementation test"
        )
        
        # Good implementation
        good_implementation = '''match n {
        0 => 0,
        1 => 1,
        _ => {
            let mut a = 0;
            let mut b = 1;
            for _ in 2..=n {
                let temp = a + b;
                a = b;
                b = temp;
            }
            b
        }
    }'''
        
        # Create scorer
        scorer = RustBuildScorer(
            use_clippy=True,
            allow_warnings=True,
            error_penalty=1.0,
            warning_penalty=0.1,
            clippy_penalty=0.05
        )
        
        # Test good implementation
        result1 = scorer._evaluate_with_test_case(test_case, good_implementation)
        
        logger.info(f"Good implementation result:")
        logger.info(f"  Score: {result1.score}")
        logger.info(f"  Passed: {result1.passed}")
        logger.info(f"  Reason: {result1.reason}")
        if result1.metadata:
            logger.info(f"  Build errors: {result1.metadata.get('build_errors', 'N/A')}")
            logger.info(f"  Build warnings: {result1.metadata.get('build_warnings', 'N/A')}")
        
        # Test case 2: Implementation with compilation error
        logger.info("\nTesting with a buggy implementation...")
        
        buggy_implementation = '''match n {
        0 => 0,
        1 => 1,
        _ => {
            let mut a = 0;
            let mut b = 1;
            for _ in 2..=n {
                let temp = a + b;  // This will cause overflow for large n
                a = b;
                b = temp;
            }
            b
        }
        // Missing closing brace - syntax error
    '''
        
        result2 = scorer._evaluate_with_test_case(test_case, buggy_implementation)
        
        logger.info(f"Buggy implementation result:")
        logger.info(f"  Score: {result2.score}")
        logger.info(f"  Passed: {result2.passed}")
        logger.info(f"  Reason: {result2.reason}")
        if result2.metadata:
            logger.info(f"  Build errors: {result2.metadata.get('build_errors', 'N/A')}")
            logger.info(f"  Build warnings: {result2.metadata.get('build_warnings', 'N/A')}")
        
        # Test case 3: Implementation with warnings
        logger.info("\nTesting with a warning-prone implementation...")
        
        warning_implementation = '''match n {
        0 => 0,
        1 => 1,
        _ => {
            let unused_var = 42;  // This will generate a warning
            let mut a = 0;
            let mut b = 1;
            for _ in 2..=n {
                let temp = a + b;
                a = b;
                b = temp;
            }
            b
        }
    }'''
        
        result3 = scorer._evaluate_with_test_case(test_case, warning_implementation)
        
        logger.info(f"Warning implementation result:")
        logger.info(f"  Score: {result3.score}")
        logger.info(f"  Passed: {result3.passed}")
        logger.info(f"  Reason: {result3.reason}")
        if result3.metadata:
            logger.info(f"  Build errors: {result3.metadata.get('build_errors', 'N/A')}")
            logger.info(f"  Build warnings: {result3.metadata.get('build_warnings', 'N/A')}")
        
        # Compare results
        print("\n" + "="*60)
        print("COMPARISON SUMMARY")
        print("="*60)
        print(f"Good implementation:    Score: {result1.score:.3f}, Passed: {result1.passed}")
        print(f"Buggy implementation:   Score: {result2.score:.3f}, Passed: {result2.passed}")
        print(f"Warning implementation: Score: {result3.score:.3f}, Passed: {result3.passed}")
        
        return [result1, result2, result3]
        
    finally:
        # Clean up
        shutil.rmtree(repo_path)
        logger.info(f"Cleaned up test repo: {repo_path}")


async def main():
    """Run the simple Rust build scorer test."""
    logger.info("Starting simple Rust Build Scorer test")
    
    try:
        results = await test_rust_build_scorer()
        logger.info("Test completed successfully!")
        
        # Save results
        results_data = []
        for i, result in enumerate(results):
            results_data.append({
                "test_case": ["good", "buggy", "warning"][i],
                "score": result.score,
                "passed": result.passed,
                "reason": result.reason,
                "metadata": result.metadata
            })
        
        with open("simple_rust_test_results.json", "w") as f:
            json.dump(results_data, f, indent=2, default=str)
        
        logger.info("Results saved to simple_rust_test_results.json")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())