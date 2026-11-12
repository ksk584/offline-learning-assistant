"""Knowledge Gap Analysis using Decision Tree and Logistic Regression models.

Analyzes student quiz performance (accuracy, response time, attempts, and difficulty)
to identify topic-specific knowledge gaps, predict gap probabilities, and steer
auto-remediation and difficulty adaptation according to the SDG 4 project methodology.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

logger = logging.getLogger(__name__)

GapTier = Literal["critical_gap", "needs_review", "proficient"]


@dataclass(frozen=True, slots=True)
class KnowledgeGapDiagnosis:
    topic: str
    mastery: float
    accuracy: float
    attempts: int
    correct: int
    avg_response_ms: int
    tier: GapTier
    tier_label: str
    gap_probability: float
    recommended_difficulty: int
    remediation_priority: int
    model_name: str
    diagnostic_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "mastery": round(self.mastery, 4),
            "accuracy": round(self.accuracy, 4),
            "attempts": self.attempts,
            "correct": self.correct,
            "avg_response_ms": self.avg_response_ms,
            "avg_response_s": round(self.avg_response_ms / 1000.0, 1),
            "tier": self.tier,
            "tier_label": self.tier_label,
            "gap_probability": round(self.gap_probability, 4),
            "recommended_difficulty": self.recommended_difficulty,
            "remediation_priority": self.remediation_priority,
            "model_name": self.model_name,
            "diagnostic_reasons": list(self.diagnostic_reasons),
        }


class KnowledgeGapClassifier:
    """Classifies topic performance into mastery tiers using Decision Tree / Logistic Regression."""

    def __init__(self, model_type: Literal["decision_tree", "logistic_regression"] = "decision_tree") -> None:
        self.model_type = model_type
        self._dt_model: Any = None
        self._lr_model: Any = None
        self._is_trained = False
        self._init_models()

    def _init_models(self) -> None:
        """Calibrate Decision Tree and Logistic Regression on assessment heuristics."""
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.tree import DecisionTreeClassifier

            # Training set mapping [accuracy (0-1), normalized_response_time (0-1), normalized_attempts (0-1), avg_difficulty (1-3)]
            # Target labels: 0: Critical Gap, 1: Needs Review, 2: Proficient
            X = [
                # Critical gaps: low accuracy regardless of time
                [0.0, 0.2, 0.2, 1.0], [0.1, 0.5, 0.3, 1.0], [0.2, 0.8, 0.5, 2.0],
                [0.25, 0.3, 0.4, 2.0], [0.3, 0.9, 0.6, 2.0], [0.15, 0.4, 0.2, 1.0],
                # Needs review: moderate accuracy, or high accuracy but very slow (hesitant)
                [0.5, 0.5, 0.4, 2.0], [0.55, 0.4, 0.5, 2.0], [0.6, 0.6, 0.6, 2.0],
                [0.65, 0.3, 0.5, 2.0], [0.45, 0.7, 0.5, 2.0], [0.75, 0.95, 0.4, 1.0],
                # Proficient: high accuracy, steady response time, good mastery
                [0.8, 0.2, 0.6, 2.0], [0.85, 0.3, 0.7, 2.0], [0.9, 0.25, 0.8, 3.0],
                [1.0, 0.15, 0.5, 3.0], [0.95, 0.2, 0.9, 3.0], [0.8, 0.35, 0.5, 2.0],
            ]
            y = [
                0, 0, 0, 0, 0, 0,
                1, 1, 1, 1, 1, 1,
                2, 2, 2, 2, 2, 2,
            ]

            dt = DecisionTreeClassifier(max_depth=4, random_state=42)
            dt.fit(X, y)
            self._dt_model = dt

            lr = LogisticRegression(C=1.0, random_state=42, max_iter=200)
            lr.fit(X, y)
            self._lr_model = lr

            self._is_trained = True
        except Exception as exc:
            logger.warning("scikit-learn classifier initialization failed: %s; using heuristic fallback", exc)
            self._is_trained = False

    def diagnose_topic(
        self,
        topic: str,
        *,
        score: float,
        attempts: int,
        correct: int,
        avg_response_ms: int = 5000,
        avg_difficulty: float = 2.0,
    ) -> KnowledgeGapDiagnosis:
        """Run ML analysis on topic metrics to identify knowledge gaps."""
        accuracy = (correct / attempts) if attempts > 0 else score
        effective_perf = 0.6 * accuracy + 0.4 * score
        # Normalize response time: 2s = 0.1, 8s = 0.4, 20s+ = 1.0
        time_factor = min(1.0, avg_response_ms / 20000.0)
        attempts_factor = min(1.0, attempts / 10.0)

        tier: GapTier = "needs_review"
        gap_prob = 0.5
        model_name = "Heuristic-Baseline"

        if self._is_trained:
            features = [[effective_perf, time_factor, attempts_factor, avg_difficulty]]
            try:
                if self.model_type == "logistic_regression" and self._lr_model is not None:
                    pred_class = int(self._lr_model.predict(features)[0])
                    proba = self._lr_model.predict_proba(features)[0]
                    # Probability of critical gap (class 0) or needs review (class 1)
                    gap_prob = float(proba[0] * 1.0 + proba[1] * 0.5)
                    model_name = "LogisticRegression"
                else:
                    pred_class = int(self._dt_model.predict(features)[0])
                    proba = self._dt_model.predict_proba(features)[0]
                    gap_prob = float(proba[0] * 1.0 + (proba[1] if len(proba) > 1 else 0.0) * 0.5)
                    model_name = "DecisionTreeClassifier"

                if pred_class == 0 or effective_perf < 0.35:
                    tier = "critical_gap"
                elif pred_class == 1 or effective_perf < 0.7:
                    tier = "needs_review"
                else:
                    tier = "proficient"
            except Exception as err:
                logger.debug("Classifier prediction failed: %s", err)
                tier, gap_prob = self._heuristic_fallback(accuracy, score, time_factor)
        else:
            tier, gap_prob = self._heuristic_fallback(accuracy, score, time_factor)

        if score < 0.35 or accuracy < 0.35:
            tier = "critical_gap"
            gap_prob = max(gap_prob, 0.8)

        # Build diagnostic reasoning
        reasons: list[str] = []
        if accuracy < 0.4:
            reasons.append(f"Low accuracy ({round(accuracy * 100)}% correct across {attempts} questions)")
        elif accuracy < 0.7:
            reasons.append(f"Moderate accuracy ({round(accuracy * 100)}%) with inconsistent retention")
        else:
            reasons.append(f"Strong accuracy ({round(accuracy * 100)}% correct)")

        if avg_response_ms > 14000:
            reasons.append(f"Hesitant response latency ({round(avg_response_ms / 1000.0, 1)}s average)")
        elif avg_response_ms < 6000 and attempts > 0:
            reasons.append(f"Fluent response speed ({round(avg_response_ms / 1000.0, 1)}s average)")

        if attempts < 2:
            reasons.append("Insufficient data: additional diagnostic practice required")

        # Map to recommended next difficulty
        if tier == "critical_gap":
            rec_diff = 1  # Foundation
            tier_label = "Critical Gap"
            priority = 1
        elif tier == "needs_review":
            rec_diff = 2  # Core
            tier_label = "Needs Review"
            priority = 2
        else:
            rec_diff = 3  # Challenge
            tier_label = "Proficient"
            priority = 3

        return KnowledgeGapDiagnosis(
            topic=topic,
            mastery=score,
            accuracy=accuracy,
            attempts=attempts,
            correct=correct,
            avg_response_ms=avg_response_ms,
            tier=tier,
            tier_label=tier_label,
            gap_probability=gap_prob,
            recommended_difficulty=rec_diff,
            remediation_priority=priority,
            model_name=model_name,
            diagnostic_reasons=tuple(reasons),
        )

    def _heuristic_fallback(self, accuracy: float, score: float, time_factor: float) -> tuple[GapTier, float]:
        effective = 0.7 * accuracy + 0.3 * score - (0.1 if time_factor > 0.7 else 0.0)
        if effective < 0.4:
            return "critical_gap", round(1.0 - effective, 3)
        if effective < 0.7:
            return "needs_review", round(1.0 - effective, 3)
        return "proficient", round(max(0.0, 1.0 - effective), 3)


# Global singleton instance
KNOWLEDGE_GAP_CLASSIFIER = KnowledgeGapClassifier()
