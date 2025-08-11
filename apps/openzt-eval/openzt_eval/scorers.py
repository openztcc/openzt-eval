"""Scoring functions for evaluations."""

from typing import Any, Dict, Optional
from dataclasses import dataclass
import logging

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