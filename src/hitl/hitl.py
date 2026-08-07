"""
Lab 11 — Part 4: Human-in-the-Loop Design
  TODO 11: Confidence Router
  TODO 12: Design 3 HITL decision points
"""
from dataclasses import dataclass


# ============================================================
# TODO 11: Implement ConfidenceRouter
#
# Route agent responses based on confidence scores:
#   - HIGH (>= 0.9): Auto-send to user
#   - MEDIUM (0.7 - 0.9): Queue for human review
#   - LOW (< 0.7): Escalate to human immediately
#
# Special case: if the action is HIGH_RISK (e.g., money transfer,
# account deletion), ALWAYS escalate regardless of confidence.
#
# Implement the route() method.
# ============================================================

HIGH_RISK_ACTIONS = [
    "transfer_money",
    "close_account",
    "change_password",
    "delete_data",
    "update_personal_info",
]


@dataclass
class RoutingDecision:
    """Result of the confidence router."""
    action: str          # "auto_send", "queue_review", "escalate"
    confidence: float
    reason: str
    priority: str        # "low", "normal", "high"
    requires_human: bool


class ConfidenceRouter:
    """Route agent responses based on confidence and risk level.

    Thresholds:
        HIGH:   confidence >= 0.9 -> auto-send
        MEDIUM: 0.7 <= confidence < 0.9 -> queue for review
        LOW:    confidence < 0.7 -> escalate to human

    High-risk actions always escalate regardless of confidence.
    """

    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def route(self, response: str, confidence: float,
              action_type: str = "general") -> RoutingDecision:
        """Route a response based on confidence score and action type.

        Args:
            response: The agent's response text
            confidence: Confidence score between 0.0 and 1.0
            action_type: Type of action (e.g., "general", "transfer_money")

        Returns:
            RoutingDecision with routing action and metadata
        """
        if action_type in HIGH_RISK_ACTIONS:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason=f"High-risk action: {action_type}",
                priority="high",
                requires_human=True,
            )
            
        if confidence >= self.HIGH_THRESHOLD:
            return RoutingDecision(
                action="auto_send",
                confidence=confidence,
                reason="High confidence",
                priority="low",
                requires_human=False,
            )
        elif confidence >= self.MEDIUM_THRESHOLD:
            return RoutingDecision(
                action="queue_review",
                confidence=confidence,
                reason="Medium confidence — needs review",
                priority="normal",
                requires_human=True,
            )
        else:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason="Low confidence — escalating",
                priority="high",
                requires_human=True,
            )


# ============================================================
# TODO 12: Design 3 HITL decision points + a review lifecycle
#
# For each decision point, define:
# - trigger: What condition activates this HITL check?
# - hitl_model: Which model? (human-in-the-loop, human-on-the-loop,
#   human-as-tiebreaker)
# - context_needed: What info does the human reviewer need?
# - example: A concrete scenario
# - approval_path: What approve/reject/timeout decision is recorded?
# - audit_fields: Which correlation ID, intent and proposed action/diff are logged?
#
# Think about real banking scenarios where human judgment is critical.
# ============================================================

hitl_decision_points = [
    {
        "id": 1,
        "name": "High-Risk Action Escalation (Money Transfer)",
        "trigger": "User requests a money transfer or beneficiary change (action in HIGH_RISK_ACTIONS).",
        "hitl_model": "human-in-the-loop (blocking)",
        "context_needed": "Diff of old/new beneficiary, transfer amount, anomaly signals (e.g. new IP login), user account history.",
        "example": "User requests transferring $50,000 to an unknown external account.",
        "approval_path": "Approve -> execute API. Reject -> notify user transaction failed. Timeout (default) -> hold/reject transaction automatically.",
        "audit_fields": "request_id, intent='transfer_money', diff='beneficiary: None -> X', reviewer_id, reviewer_decision, audit_layer='ActionGateway'",
    },
    {
        "id": 2,
        "name": "Medium Confidence Response Queue",
        "trigger": "Confidence score is between 0.70 and 0.89.",
        "hitl_model": "human-on-the-loop (asynchronous queue)",
        "context_needed": "User chat history (last 5 messages), the LLM's drafted response, and the exact confidence score.",
        "example": "User asks 'Can I combine my auto loan and mortgage?' and the agent drafts a complex reply but is only 75% confident.",
        "approval_path": "Approve -> send drafted text. Reject -> human rewrites the response. Timeout -> send generic fallback ('Please call support').",
        "audit_fields": "request_id, intent='loan_inquiry', proposed_response='Drafted text...', reviewer_decision='rewritten', audit_layer='ResponseRouter'",
    },
    {
        "id": 3,
        "name": "Low Confidence / Unsafe Policy Violation",
        "trigger": "Confidence < 0.70 OR OutputGuardrail flags response as UNSAFE.",
        "hitl_model": "human-in-the-loop (immediate takeover)",
        "context_needed": "Full chat transcript, flagged violation reason (e.g., 'PII detected'), user profile details.",
        "example": "User is extremely angry about hidden fees, complains using profanity, and agent confidence drops to 0.4.",
        "approval_path": "Human takes over live chat. Timeout -> Send automated apology message and create a CRM support ticket.",
        "audit_fields": "request_id, intent='complaint', violation_reason='low_confidence', reviewer_decision='human_takeover', audit_layer='SafetyFilter'",
    },
]


# ============================================================
# Quick tests
# ============================================================

def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_cases = [
        ("Balance inquiry", 0.95, "general"),
        ("Interest rate question", 0.82, "general"),
        ("Ambiguous request", 0.55, "general"),
        ("Transfer $50,000", 0.98, "transfer_money"),
        ("Close my account", 0.91, "close_account"),
    ]

    print("Testing ConfidenceRouter:")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Conf':<6} {'Action Type':<18} {'Decision':<15} {'Priority':<10} {'Human?'}")
    print("-" * 80)

    for scenario, conf, action_type in test_cases:
        decision = router.route(scenario, conf, action_type)
        print(
            f"{scenario:<25} {conf:<6.2f} {action_type:<18} "
            f"{decision.action:<15} {decision.priority:<10} "
            f"{'Yes' if decision.requires_human else 'No'}"
        )

    print("=" * 80)


def test_hitl_points():
    """Display HITL decision points."""
    print("\nHITL Decision Points:")
    print("=" * 60)
    for point in hitl_decision_points:
        print(f"\n  Decision Point #{point['id']}: {point['name']}")
        print(f"    Trigger:  {point['trigger']}")
        print(f"    Model:    {point['hitl_model']}")
        print(f"    Context:  {point['context_needed']}")
        print(f"    Example:  {point['example']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
