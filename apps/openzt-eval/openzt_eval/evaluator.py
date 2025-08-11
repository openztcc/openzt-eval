"""Main evaluation logic using braintrust."""

from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
import asyncio
import logging
from datetime import datetime

try:
    import braintrust
except ImportError:
    braintrust = None

try:
    from autoevals import Levenshtein, ClosedQA, Battle, LLMClassifier
    AUTOEVALS_AVAILABLE = True
except ImportError:
    Levenshtein = None
    ClosedQA = None
    Battle = None
    LLMClassifier = None
    AUTOEVALS_AVAILABLE = False

from .models import ModelLoader, ModelConfig
from .scorers import BaseScorer, BasicResponseScorer, ScorerResult

logger = logging.getLogger(__name__)


@dataclass
class EvalCase:
    """A single evaluation test case."""
    name: str
    prompt: str
    expected: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EvalResult:
    """Result of an evaluation."""
    model_name: str
    case_name: str
    prompt: str
    response: str
    scores: Dict[str, ScorerResult]
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def passed(self) -> bool:
        """Check if all scorers passed."""
        return all(score.passed for score in self.scores.values())
    
    @property
    def average_score(self) -> float:
        """Calculate average score across all scorers."""
        if not self.scores:
            return 0.0
        return sum(s.score for s in self.scores.values()) / len(self.scores)


class Evaluator:
    """Main evaluator that runs test cases against models."""
    
    def __init__(
        self,
        model_loader: ModelLoader,
        scorers: Optional[List[Union[BaseScorer, Callable]]] = None,
        use_braintrust: bool = True,
        project_name: str = "openzt-eval",
        use_autoevals: bool = True
    ):
        self.model_loader = model_loader
        self.scorers = scorers or [BasicResponseScorer()]
        self.use_braintrust = use_braintrust and braintrust is not None
        self.project_name = project_name
        self.use_autoevals = use_autoevals and AUTOEVALS_AVAILABLE
        self.autoevals_scorers = []
        
        # Add default autoevals scorers if available
        if self.use_autoevals and not scorers:
            self._setup_default_autoevals()
        
        if self.use_braintrust:
            try:
                self.bt_project = braintrust.init(project=project_name)
                logger.info(f"Initialized Braintrust project: {project_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize Braintrust: {e}")
                self.use_braintrust = False
                self.bt_project = None
        else:
            self.bt_project = None
    
    def _setup_default_autoevals(self):
        """Setup default autoevals scorers."""
        if not AUTOEVALS_AVAILABLE:
            return
        
        # Add Levenshtein for string similarity when expected output exists
        self.autoevals_scorers.append(("levenshtein", Levenshtein))
        logger.info("Added Levenshtein scorer from autoevals")
    
    async def evaluate_case(
        self,
        model_name: str,
        case: EvalCase
    ) -> EvalResult:
        """Evaluate a single test case on a model."""
        model = self.model_loader.get_model(model_name)
        if not model:
            raise ValueError(f"Model {model_name} not loaded")
        
        # Generate response
        start_time = asyncio.get_event_loop().time()
        try:
            response = await model.generate(case.prompt)
        except Exception as e:
            logger.error(f"Error generating response for {model_name}: {e}")
            response = f"ERROR: {str(e)}"
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        
        # Score the response with custom scorers
        scores = {}
        for scorer in self.scorers:
            if isinstance(scorer, BaseScorer):
                scores[scorer.name] = scorer.score(case.prompt, response, case.expected)
            elif callable(scorer):
                # Handle autoevals or other callable scorers
                try:
                    result = scorer(output=response, expected=case.expected)
                    scores[getattr(scorer, '__name__', 'custom')] = ScorerResult(
                        score=result.score if hasattr(result, 'score') else result,
                        passed=result.score >= 0.5 if hasattr(result, 'score') else result > 0.5,
                        reason=result.rationale if hasattr(result, 'rationale') else None
                    )
                except Exception as e:
                    logger.warning(f"Error running scorer {scorer}: {e}")
        
        # Apply autoevals scorers if expected output exists
        if self.use_autoevals and case.expected:
            for name, scorer_class in self.autoevals_scorers:
                try:
                    result = scorer_class()(output=response, expected=case.expected)
                    scores[name] = ScorerResult(
                        score=result.score,
                        passed=result.score >= 0.5,
                        reason=getattr(result, 'rationale', None),
                        metadata=result.metadata if hasattr(result, 'metadata') else None
                    )
                except Exception as e:
                    logger.warning(f"Error running autoevals scorer {name}: {e}")
        
        result = EvalResult(
            model_name=model_name,
            case_name=case.name,
            prompt=case.prompt,
            response=response,
            scores=scores,
            duration_ms=duration_ms,
            metadata=case.metadata
        )
        
        # Log to Braintrust if enabled
        if self.use_braintrust and self.bt_project:
            try:
                self.bt_project.log(
                    input=case.prompt,
                    output=response,
                    expected=case.expected,
                    scores={name: score.score for name, score in scores.items()},
                    metadata={
                        "model": model_name,
                        "case": case.name,
                        "duration_ms": duration_ms,
                        "passed": result.passed,
                        **(case.metadata or {})
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log to Braintrust: {e}")
        
        return result
    
    async def evaluate(
        self,
        cases: List[EvalCase],
        model_names: Optional[List[str]] = None
    ) -> List[EvalResult]:
        """Run evaluation cases against models."""
        if model_names is None:
            model_names = list(self.model_loader.models.keys())
        
        results = []
        total = len(cases) * len(model_names)
        completed = 0
        
        for model_name in model_names:
            logger.info(f"Evaluating model: {model_name}")
            for case in cases:
                logger.info(f"  Running case: {case.name}")
                result = await self.evaluate_case(model_name, case)
                results.append(result)
                
                completed += 1
                logger.info(
                    f"  [{completed}/{total}] {model_name}/{case.name}: "
                    f"{'PASS' if result.passed else 'FAIL'} "
                    f"(score: {result.average_score:.2f})"
                )
        
        # Finalize Braintrust experiment if used
        if self.use_braintrust and self.bt_project:
            try:
                summary = self.bt_project.summarize()
                logger.info(f"Braintrust summary: {summary}")
            except Exception as e:
                logger.warning(f"Failed to summarize Braintrust experiment: {e}")
        
        return results
    
    def print_summary(self, results: List[EvalResult]):
        """Print a summary of evaluation results."""
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        # Group results by model
        by_model = {}
        for result in results:
            if result.model_name not in by_model:
                by_model[result.model_name] = []
            by_model[result.model_name].append(result)
        
        # Create summary table
        table = Table(title="Evaluation Summary")
        table.add_column("Model", style="cyan")
        table.add_column("Cases", justify="right")
        table.add_column("Passed", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Avg Score", justify="right")
        table.add_column("Avg Duration (ms)", justify="right")
        
        for model_name, model_results in by_model.items():
            passed = sum(1 for r in model_results if r.passed)
            failed = len(model_results) - passed
            avg_score = sum(r.average_score for r in model_results) / len(model_results)
            avg_duration = sum(r.duration_ms for r in model_results) / len(model_results)
            
            table.add_row(
                model_name,
                str(len(model_results)),
                str(passed),
                str(failed),
                f"{avg_score:.2f}",
                f"{avg_duration:.1f}"
            )
        
        console.print(table)