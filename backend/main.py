from __future__ import annotations

import os
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dotenv import load_dotenv

from .agent_simulator import SimulatedBuyer
from .ai_buyer import AIBuyer
from .ai_parser import AIParser
from .database import AuditDatabase
from .models import ApprovalRecord, PolicyDecision, ProposedTransaction, UserIntent
from .policy_engine import PolicyEngine
from .razorpay_service import RazorpayService

load_dotenv()

app = FastAPI(title="Agent Leash API", version="0.1.0")

# Placeholder services
policy_engine = PolicyEngine()
database = AuditDatabase()
razorpay_service = RazorpayService()
simulator = SimulatedBuyer()
parser: AIParser | None = None
ai_buyer: AIBuyer | None = None

AI_BUYER_CATALOG = [
    {
        "product_id": "black-running-shoes",
        "product_name": "Black Running Shoes",
        "unit_price": 2799,
        "currency": "INR",
        "merchant_id": "merchant-demo",
        "category": "footwear",
        "color": "black",
        "size": "9",
        "is_subscription": False,
        "is_addon": False,
    },
    {
        "product_id": "blue-backpack",
        "product_name": "Blue Backpack",
        "unit_price": 1499,
        "currency": "INR",
        "merchant_id": "merchant-demo",
        "category": "backpack",
        "color": "blue",
        "size": None,
        "is_subscription": False,
        "is_addon": False,
    },
    {
        "product_id": "wireless-headphones",
        "product_name": "Wireless Headphones",
        "unit_price": 2499,
        "currency": "INR",
        "merchant_id": "merchant-demo",
        "category": "headphones",
        "color": None,
        "size": None,
        "is_subscription": False,
        "is_addon": False,
    },
    {
        "product_id": "smartwatch",
        "product_name": "Smartwatch",
        "unit_price": 3999,
        "currency": "INR",
        "merchant_id": "merchant-demo",
        "category": "electronics",
        "color": None,
        "size": None,
        "is_subscription": False,
        "is_addon": False,
    },
    {
        "product_id": "laptop",
        "product_name": "Laptop",
        "unit_price": 45000,
        "currency": "INR",
        "merchant_id": "merchant-demo",
        "category": "electronics",
        "color": None,
        "size": None,
        "is_subscription": False,
        "is_addon": False,
    },
]


class HealthResponse(BaseModel):
    status: str
    service: str


class AgentBuyRequest(BaseModel):
    instruction: str
    request_id: Optional[str] = None


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="agent-leash-backend")


@app.post("/evaluate")
def evaluate_transaction(user_intent: UserIntent, transaction: ProposedTransaction) -> PolicyDecision:
    """Evaluate a proposed AI cart/payment action against policy.

    This is a minimal skeleton endpoint for the first task.
    """
    decision = policy_engine.evaluate(user_intent, transaction)
    transaction.transaction_id = decision.transaction_id
    database.log_decision(
        transaction_id=decision.transaction_id,
        user_id=transaction.user_id,
        decision=decision.decision,
        reason=decision.reason,
        risk_score=decision.risk_score,
        total_amount=transaction.total_amount,
        currency=transaction.currency,
    )
    return decision


@app.post("/parse-intent")
def parse_intent(instruction: str) -> UserIntent:
    global parser
    if parser is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        parser = AIParser(api_key=api_key)
    return parser.parse(instruction)


@app.post("/agent/buy")
def agent_buy(payload: AgentBuyRequest) -> dict:
    """Parse an instruction, select one catalog product, and evaluate it."""
    if not payload.instruction.strip():
        raise HTTPException(status_code=400, detail="Instruction cannot be empty.")

    global parser, ai_buyer
    try:
        if parser is None:
            parser = AIParser(api_key=os.getenv("OPENROUTER_API_KEY"))
        user_intent = parser.parse(payload.instruction)
    except Exception as exc:
        status_code = 503 if "quota" in str(exc).lower() else 502
        raise HTTPException(status_code=status_code, detail=f"Intent parsing failed: {exc}") from exc

    try:
        if ai_buyer is None:
            ai_buyer = AIBuyer(api_key=os.getenv("OPENROUTER_API_KEY"))
        proposal = ai_buyer.propose_transaction(user_intent, AI_BUYER_CATALOG)
        # Detect subscription/addon explicitly requested in instruction.
        # The proposed catalog product always has is_subscription=False, is_addon=False.
        # If the user instruction explicitly REQUESTS a subscription or add-on, we must
        # flag it on the proposed item so the policy engine can correctly BLOCK it.
        instruction_lower = payload.instruction.lower()

        # Detect subscription/addon explicitly REQUESTED in the instruction.
        # We use positive-request phrases only, so "no subscription" / "no add-ons"
        # (negation) does NOT trigger this flag.
        import re as _re

        def _is_positively_requested(text: str, phrases: list[str]) -> bool:
            """Return True if any phrase appears without a preceding negation word."""
            negations = {"no", "not", "without", "don't", "dont", "never", "avoid", "exclude", "skip", "or"}
            for phrase in phrases:
                for m in _re.finditer(_re.escape(phrase), text):
                    # Grab the four words immediately before the match
                    before = text[:m.start()].split()[-4:]
                    if not any(w.rstrip(",.!?;") in negations for w in before):
                        return True
            return False

        # Positive subscription request phrases — unambiguously affirmative
        sub_phrases = [
            "subscribe me", "sign me up for", "add subscription", "add a subscription",
            "monthly membership", "monthly premium", "premium membership", "recurring",
            "membership plan", "monthly plan", "annual plan",
        ]
        # Positive add-on request phrases — unambiguously affirmative (no bare "add-on")
        addon_phrases = [
            "add warranty", "add a warranty", "add extended warranty", "extended warranty",
            "protection plan", "extended care", "add addon", "include an add-on",
            "add an add-on", "include a warranty",
        ]

        if _is_positively_requested(instruction_lower, sub_phrases):
            for item in proposal.items:
                item.is_subscription = True
        if _is_positively_requested(instruction_lower, addon_phrases):
            for item in proposal.items:
                item.is_addon = True
    except Exception as exc:
        status_code = 503 if "quota" in str(exc).lower() else 502
        raise HTTPException(status_code=status_code, detail=f"AI Buyer failed: {exc}") from exc

    proposal.transaction_id = payload.request_id or uuid.uuid4().hex[:16]

    try:
        decision = policy_engine.evaluate(user_intent, proposal)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Policy evaluation failed: {exc}") from exc

    proposal.transaction_id = decision.transaction_id
    database.log_decision(
        transaction_id=decision.transaction_id,
        user_id=proposal.user_id,
        decision=decision.decision,
        reason=decision.reason,
        risk_score=decision.risk_score,
        total_amount=proposal.total_amount,
        currency=proposal.currency,
        idempotency_key=payload.request_id,
    )
    return {
        "user_intent": user_intent.model_dump(mode="json"),
        "ai_buyer_proposal": proposal.model_dump(mode="json"),
        "decision": decision.decision,
        "risk_score": decision.risk_score,
        "violated_rules": decision.violated_rules,
        "policy_reasons": decision.reasons,
        "transaction_id": decision.transaction_id,
        "payment_ready": decision.decision == "ALLOW",
    }


@app.post("/approval")
def record_human_approval(payload: ApprovalRecord) -> dict:
    if payload.original_decision != "ASK":
        raise HTTPException(status_code=400, detail="original_decision must be 'ASK'")
    if payload.human_decision not in {"APPROVE", "REJECT"}:
        raise HTTPException(status_code=400, detail="human_decision must be APPROVE or REJECT")
    if not payload.transaction_id:
        raise HTTPException(status_code=400, detail="transaction_id is required")
    if not payload.reviewer:
        raise HTTPException(status_code=400, detail="reviewer is required")

    record = database.record_approval(
        transaction_id=payload.transaction_id,
        original_decision=payload.original_decision,
        human_decision=payload.human_decision,
        reviewer=payload.reviewer,
        note=payload.note,
    )

    return {
        "status": "recorded",
        "transaction_id": record["transaction_id"],
        "human_decision": record["human_decision"],
        "reviewer": record["reviewer"],
        "timestamp": record["timestamp"],
    }


@app.post("/transactions/{transaction_id}/order")
def create_transaction_order(transaction_id: str) -> dict:
    decision = database.get_latest_decision_for_transaction(transaction_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="No policy decision recorded for this transaction.")

    decision_name = str(decision.get("decision", "")).upper()
    if decision_name == "BLOCK":
        raise HTTPException(status_code=403, detail="Transaction is blocked; Razorpay order creation is not allowed.")
    if decision_name == "ASK":
        approval = database.get_latest_approval_for_transaction(transaction_id)
        if approval is None or str(approval.get("human_decision", "")).upper() != "APPROVE":
            raise HTTPException(status_code=403, detail="Human approval is required before creating a Razorpay order.")

    amount = float(decision.get("total_amount") or 0.0)
    currency = str(decision.get("currency") or "INR").upper()

    try:
        order = razorpay_service.create_test_order(
            amount=amount,
            currency=currency,
            transaction_id=transaction_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Razorpay order creation failed: {exc}") from exc

    database.save_razorpay_order(
        transaction_id=transaction_id,
        razorpay_order_id=str(order.get("id") or order.get("razorpay_order_id") or transaction_id),
        amount=int(order.get("amount", 0)),
        currency=str(order.get("currency") or currency).upper(),
        status=str(order.get("status") or "created"),
    )

    amount_rupees = int((order.get("amount_rupees") if order.get("amount_rupees") is not None else int(order.get("amount", 0)) / 100))
    return {
        "transaction_id": transaction_id,
        "policy_decision": decision_name,
        "razorpay_order_id": str(order.get("id") or order.get("razorpay_order_id") or transaction_id),
        "amount": amount_rupees,
        "currency": str(order.get("currency") or currency).upper(),
        "status": str(order.get("status") or "created"),
    }


@app.get("/")
def root() -> dict:
    return {"message": "Agent Leash backend is running."}


@app.get("/audit")
def audit_trail() -> list[dict]:
    return database.list_audit_records()


def _demo_user_intent_for(scenario_name: str) -> UserIntent:
    scenario = scenario_name.upper()
    if scenario == "SAFE_PURCHASE":
        return UserIntent(
            instruction="Buy black running shoes, size 9, under ₹3000. No extras.",
            product_name="Black Running Shoes",
            max_amount=3000,
            currency="INR",
            categories=["footwear"],
            allowed_categories=["footwear"],
            allowed_colors=["black"],
            allowed_sizes=["9"],
            allow_subscription=False,
            allow_addons=False,
            daily_limit=5000,
            session_limit=5000,
            review_threshold=None,
            previous_approved_amounts=[],
        )

    if scenario == "UNAUTHORIZED_ADDON":
        return UserIntent(
            instruction="Buy black running shoes, size 9, under ₹3000. No extras.",
            product_name="Black Running Shoes",
            max_amount=3000,
            currency="INR",
            categories=["footwear"],
            allowed_categories=["footwear"],
            allowed_colors=["black"],
            allowed_sizes=["9"],
            allow_subscription=False,
            allow_addons=False,
            daily_limit=5000,
            session_limit=5000,
            review_threshold=None,
            previous_approved_amounts=[],
        )

    if scenario == "UNAUTHORIZED_SUBSCRIPTION":
        return UserIntent(
            instruction="Buy black running shoes, size 9, under ₹3000. No extras.",
            product_name="Black Running Shoes",
            max_amount=3000,
            currency="INR",
            categories=["footwear"],
            allowed_categories=["footwear"],
            allowed_colors=["black"],
            allowed_sizes=["9"],
            allow_subscription=False,
            allow_addons=False,
            daily_limit=5000,
            session_limit=5000,
            review_threshold=None,
            previous_approved_amounts=[],
        )

    if scenario == "OVER_LIMIT":
        return UserIntent(
            instruction="Buy black running shoes, size 9, under ₹3000. No extras.",
            product_name="Black Running Shoes",
            max_amount=3000,
            currency="INR",
            categories=["footwear"],
            allowed_categories=["footwear"],
            allowed_colors=["black"],
            allowed_sizes=["9"],
            allow_subscription=False,
            allow_addons=False,
            daily_limit=5000,
            session_limit=5000,
            review_threshold=None,
            previous_approved_amounts=[],
        )

    if scenario == "AGGREGATE_SPLIT":
        return UserIntent(
            instruction="Buy black running shoes, size 9, under ₹3000. No extras.",
            product_name="Black Running Shoes",
            max_amount=3000,
            currency="INR",
            categories=["footwear"],
            allowed_categories=["footwear"],
            allowed_colors=["black"],
            allowed_sizes=["9"],
            allow_subscription=False,
            allow_addons=False,
            daily_limit=3000,
            session_limit=3000,
            review_threshold=None,
            previous_approved_amounts=[1800],
        )

    raise HTTPException(status_code=404, detail=f"Unknown demo scenario: {scenario_name}")


@app.get("/demo/scenarios")
def demo_scenarios() -> list[dict]:
    return simulator.scenario_list()


class DemoRequest(BaseModel):
    request_id: Optional[str] = None


@app.post("/demo/ask")
def demo_ask_evaluation(payload: Optional[DemoRequest] = None) -> dict:
    """Evaluate a valid demo purchase above its human-review threshold."""
    user_intent = UserIntent(
        instruction="Buy black running shoes, size 9, under ₹3000. Human confirmation required for this transaction.",
        product_name="Black Running Shoes",
        max_amount=3000,
        currency="INR",
        categories=["footwear"],
        allowed_categories=["footwear"],
        allowed_colors=["black"],
        allowed_sizes=["9"],
        allow_subscription=False,
        allow_addons=False,
        daily_limit=5000,
        session_limit=5000,
        review_threshold=2500,
        previous_approved_amounts=[],
    )
    global ai_buyer
    if ai_buyer is None:
        ai_buyer = AIBuyer(api_key=os.getenv("OPENROUTER_API_KEY"))
    proposed_transaction = ai_buyer.propose_transaction(user_intent, [AI_BUYER_CATALOG[0]])
    req_id = payload.request_id if payload else None
    proposed_transaction.transaction_id = req_id or uuid.uuid4().hex[:16]

    decision = policy_engine.evaluate(user_intent, proposed_transaction)
    proposed_transaction.transaction_id = decision.transaction_id
    database.log_decision(
        transaction_id=decision.transaction_id,
        user_id=proposed_transaction.user_id,
        decision=decision.decision,
        reason=decision.reason,
        risk_score=decision.risk_score,
        total_amount=proposed_transaction.total_amount,
        currency=proposed_transaction.currency,
        idempotency_key=req_id,
    )
    return {
        "user_intent": user_intent.model_dump(mode="json"),
        "proposed_transaction": proposed_transaction.model_dump(mode="json"),
        "policy_decision": decision.model_dump(mode="json"),
    }


@app.post("/demo/scenarios/{scenario_name}")
def demo_scenario_evaluation(scenario_name: str, payload: Optional[DemoRequest] = None) -> dict:
    scenario = scenario_name.upper()
    if scenario not in simulator.SCENARIO_DESCRIPTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown demo scenario: {scenario_name}")

    user_intent = _demo_user_intent_for(scenario)
    proposed_transaction = simulator.generate_transaction(scenario)
    if scenario == "AGGREGATE_SPLIT":
        proposed_transaction = simulator.generate_transactions(scenario)[1]

    req_id = payload.request_id if payload else None
    proposed_transaction.transaction_id = req_id or uuid.uuid4().hex[:16]

    decision = policy_engine.evaluate(user_intent, proposed_transaction)
    proposed_transaction.transaction_id = decision.transaction_id
    database.log_decision(
        transaction_id=decision.transaction_id,
        user_id=proposed_transaction.user_id,
        decision=decision.decision,
        reason=decision.reason,
        risk_score=decision.risk_score,
        total_amount=proposed_transaction.total_amount,
        currency=proposed_transaction.currency,
        idempotency_key=req_id,
    )
    return {
        "user_intent": user_intent.model_dump(mode="json"),
        "proposed_transaction": proposed_transaction.model_dump(mode="json"),
        "policy_decision": decision.model_dump(mode="json"),
    }
