"""Scoring functions for evaluations."""

from typing import Any, Dict, Optional, List
from dataclasses import dataclass
import logging
import tempfile
import shutil
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import git

logger = logging.getLogger(__name__)


@dataclass
class ScorerResult:
    """Result from a scorer."""
    score: float
    passed: bool
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseScorer:
    """Base class for eval scorers."""
    
    def __init__(self, name: str):
        self.name = name
    
    def score(self, prompt: str, response: str, expected: Optional[str] = None) -> ScorerResult:
        """Score a model response."""
        raise NotImplementedError


class BasicResponseScorer(BaseScorer):
    """Basic scorer that just checks if we got a non-empty response."""
    
    def __init__(self, min_length: int = 1):
        super().__init__("basic_response")
        self.min_length = min_length
    
    def score(self, prompt: str, response: str, expected: Optional[str] = None) -> ScorerResult:
        """Check if response is non-empty and meets minimum length."""
        if not response:
            return ScorerResult(
                score=0.0,
                passed=False,
                reason="Empty response"
            )
        
        response_clean = response.strip()
        
        # Check for error markers
        if response_clean.startswith("ERROR:"):
            return ScorerResult(
                score=0.0,
                passed=False,
                reason=f"Error in response: {response_clean[:100]}"
            )
        
        # Check minimum length
        if len(response_clean) < self.min_length:
            return ScorerResult(
                score=0.5,
                passed=False,
                reason=f"Response too short (length: {len(response_clean)}, required: {self.min_length})"
            )
        
        # Basic success - we got a response
        return ScorerResult(
            score=1.0,
            passed=True,
            reason="Valid response received",
            metadata={
                "response_length": len(response_clean),
                "prompt_length": len(prompt)
            }
        )


class LengthScorer(BaseScorer):
    """Scorer that checks response length."""
    
    def __init__(self, min_length: int = 10, max_length: Optional[int] = None):
        super().__init__("length")
        self.min_length = min_length
        self.max_length = max_length
    
    def score(self, prompt: str, response: str, expected: Optional[str] = None) -> ScorerResult:
        """Score based on response length."""
        length = len(response.strip())
        
        if length < self.min_length:
            return ScorerResult(
                score=length / self.min_length,
                passed=False,
                reason=f"Too short: {length} < {self.min_length}"
            )
        
        if self.max_length and length > self.max_length:
            return ScorerResult(
                score=0.5,
                passed=False,
                reason=f"Too long: {length} > {self.max_length}"
            )
        
        return ScorerResult(
            score=1.0,
            passed=True,
            reason=f"Good length: {length}",
            metadata={"length": length}
        )


class ContainsScorer(BaseScorer):
    """Scorer that checks if response contains certain text."""
    
    def __init__(self, required_text: str, case_sensitive: bool = False):
        super().__init__(f"contains_{required_text[:20]}")
        self.required_text = required_text
        self.case_sensitive = case_sensitive
    
    def score(self, prompt: str, response: str, expected: Optional[str] = None) -> ScorerResult:
        """Check if response contains required text."""
        if self.case_sensitive:
            contains = self.required_text in response
        else:
            contains = self.required_text.lower() in response.lower()
        
        return ScorerResult(
            score=1.0 if contains else 0.0,
            passed=contains,
            reason=f"{'Contains' if contains else 'Missing'}: '{self.required_text}'"
        )


@dataclass
class RustBuildTestCase:
    """Test case for Rust build evaluation."""
    repo_url: str
    tag_or_branch: str
    file_path: str
    replacement_target: str
    description: Optional[str] = None


class RustBuildScorer(BaseScorer):
    """Scorer that evaluates LLM output by substituting it into a Rust project and building."""
    
    def __init__(self, 
                 use_clippy: bool = True,
                 allow_warnings: bool = True,
                 error_penalty: float = 1.0,
                 warning_penalty: float = 0.1,
                 clippy_penalty: float = 0.05,
                 timeout: int = 300):
        """Initialize the Rust build scorer.
        
        Args:
            use_clippy: Whether to run clippy in addition to build
            allow_warnings: Whether warnings are acceptable (affects pass/fail)
            error_penalty: Score penalty per error (default: 1.0 - full penalty)
            warning_penalty: Score penalty per warning (default: 0.1)
            clippy_penalty: Score penalty per clippy lint (default: 0.05)
            timeout: Timeout in seconds for build operations
        """
        super().__init__("rust_build")
        self.use_clippy = use_clippy
        self.allow_warnings = allow_warnings
        self.error_penalty = error_penalty
        self.warning_penalty = warning_penalty
        self.clippy_penalty = clippy_penalty
        self.timeout = timeout
    
    def score(self, prompt: str, response: str, expected: Optional[str] = None) -> ScorerResult:
        """Score the response by building a Rust project with the substitution.
        
        The expected parameter should be a JSON string containing RustBuildTestCase data:
        {
            "repo_url": "https://github.com/user/repo",
            "tag_or_branch": "main",
            "file_path": "src/lib.rs", 
            "replacement_target": "// TODO: implement this function",
            "description": "Optional description"
        }
        """
        if not expected:
            return ScorerResult(
                score=0.0,
                passed=False,
                reason="No test case configuration provided"
            )
        
        try:
            import json
            test_case_data = json.loads(expected)
            test_case = RustBuildTestCase(**test_case_data)
        except (json.JSONDecodeError, TypeError) as e:
            return ScorerResult(
                score=0.0,
                passed=False,
                reason=f"Invalid test case configuration: {e}"
            )
        
        return self._evaluate_with_test_case(test_case, response)
    
    def _evaluate_with_test_case(self, test_case: RustBuildTestCase, response: str) -> ScorerResult:
        """Evaluate the response with a specific test case."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # Clone the repository
                repo_path = self._clone_repository(test_case.repo_url, test_case.tag_or_branch, temp_path)
                
                # Perform the substitution
                target_file = repo_path / test_case.file_path
                if not target_file.exists():
                    return ScorerResult(
                        score=0.0,
                        passed=False,
                        reason=f"Target file not found: {test_case.file_path}"
                    )
                
                self._perform_substitution(target_file, test_case.replacement_target, response)
                
                # Run cargo build and optionally clippy
                build_result = self._run_cargo_build(repo_path)
                clippy_result = None
                if self.use_clippy:
                    clippy_result = self._run_cargo_clippy(repo_path)
                
                # Calculate score
                return self._calculate_score(build_result, clippy_result, test_case)
                
            except Exception as e:
                logger.error(f"Error during Rust build evaluation: {e}")
                return ScorerResult(
                    score=0.0,
                    passed=False,
                    reason=f"Evaluation failed: {str(e)}"
                )
    
    def _clone_repository(self, repo_url: str, tag_or_branch: str, temp_path: Path) -> Path:
        """Clone the repository to a temporary directory."""
        repo_path = temp_path / "repo"
        
        logger.info(f"Cloning {repo_url} (branch: {tag_or_branch}) to {repo_path}")
        
        # Clone the repository
        repo = git.Repo.clone_from(repo_url, repo_path)
        
        # Checkout the specific tag or branch
        try:
            repo.git.checkout(tag_or_branch)
        except git.exc.GitCommandError as e:
            logger.warning(f"Failed to checkout {tag_or_branch}: {e}")
            # Continue with default branch
        
        return repo_path
    
    def _perform_substitution(self, target_file: Path, replacement_target: str, replacement_text: str):
        """Replace the target string with the LLM response in the target file."""
        logger.info(f"Performing substitution in {target_file}")
        
        content = target_file.read_text(encoding='utf-8')
        
        if replacement_target not in content:
            raise ValueError(f"Replacement target not found in {target_file}: {replacement_target}")
        
        # Perform the replacement
        new_content = content.replace(replacement_target, replacement_text)
        target_file.write_text(new_content, encoding='utf-8')
        
        logger.info(f"Substituted {len(replacement_target)} chars with {len(replacement_text)} chars")
    
    def _run_cargo_build(self, repo_path: Path) -> Any:
        """Run cargo build and return the result."""
        try:
            from cargo_orchestrator import CargoBuilder
            
            builder = CargoBuilder(root_dir=repo_path)
            result = builder.build()
            
            logger.info(f"Cargo build completed: success={result.success}, "
                       f"messages={len(result.messages)}, return_code={result.return_code}")
            
            return result
        except ImportError:
            raise RuntimeError("cargo-orchestrator library is required for RustBuildScorer")
    
    def _run_cargo_clippy(self, repo_path: Path) -> Any:
        """Run cargo clippy and return the result."""
        try:
            from cargo_orchestrator import CargoBuilder
            
            builder = CargoBuilder(root_dir=repo_path)
            result = builder.clippy()
            
            logger.info(f"Cargo clippy completed: success={result.success}, "
                       f"messages={len(result.messages)}, return_code={result.return_code}")
            
            return result
        except ImportError:
            raise RuntimeError("cargo-orchestrator library is required for RustBuildScorer")
    
    def _calculate_score(self, build_result: Any, clippy_result: Any, test_case: RustBuildTestCase) -> ScorerResult:
        """Calculate the final score based on build and clippy results."""
        from cargo_orchestrator.parser import MessageLevel
        
        # Count different types of messages
        build_errors = sum(1 for msg in build_result.messages if msg.level == MessageLevel.ERROR)
        build_warnings = sum(1 for msg in build_result.messages if msg.level == MessageLevel.WARNING)
        
        clippy_errors = 0
        clippy_warnings = 0
        clippy_lints = 0
        
        if clippy_result:
            clippy_errors = sum(1 for msg in clippy_result.messages if msg.level == MessageLevel.ERROR)
            clippy_warnings = sum(1 for msg in clippy_result.messages if msg.level == MessageLevel.WARNING)
            # Count clippy-specific lints
            clippy_lints = sum(1 for msg in clippy_result.messages 
                             if msg.code and "clippy::" in msg.code)
        
        total_errors = build_errors + clippy_errors
        total_warnings = build_warnings + clippy_warnings
        
        # Calculate score (start from 1.0 and subtract penalties)
        score = 1.0
        score -= total_errors * self.error_penalty
        score -= total_warnings * self.warning_penalty
        score -= clippy_lints * self.clippy_penalty
        
        # Ensure score is between 0 and 1
        score = max(0.0, min(1.0, score))
        
        # Determine if it passes
        build_passed = build_result.success
        clippy_passed = clippy_result.success if clippy_result else True
        
        # Pass if build succeeds and (warnings allowed or no warnings)
        passed = build_passed and clippy_passed and (self.allow_warnings or total_warnings == 0)
        
        # Generate reason
        reason_parts = []
        if not build_passed:
            reason_parts.append(f"Build failed with {build_errors} errors")
        if not clippy_passed:
            reason_parts.append(f"Clippy failed with {clippy_errors} errors")
        if total_warnings > 0:
            reason_parts.append(f"{total_warnings} warnings")
        if clippy_lints > 0:
            reason_parts.append(f"{clippy_lints} clippy lints")
        
        if not reason_parts:
            reason = "Build and clippy passed successfully"
        else:
            reason = "; ".join(reason_parts)
        
        metadata = {
            "build_success": build_result.success,
            "build_errors": build_errors,
            "build_warnings": build_warnings,
            "build_return_code": build_result.return_code,
            "test_case": {
                "repo_url": test_case.repo_url,
                "tag_or_branch": test_case.tag_or_branch,
                "file_path": test_case.file_path,
                "description": test_case.description
            }
        }
        
        if clippy_result:
            metadata.update({
                "clippy_success": clippy_result.success,
                "clippy_errors": clippy_errors,
                "clippy_warnings": clippy_warnings,
                "clippy_lints": clippy_lints,
                "clippy_return_code": clippy_result.return_code
            })
        
        return ScorerResult(
            score=score,
            passed=passed,
            reason=reason,
            metadata=metadata
        )