from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class CartItem(BaseModel):
    """Represents an item proposed for purchase."""

    product_name: str
    quantity: int = Field(default=1, ge=1)
    unit_price: Optional[float] = Field(default=0.0, ge=0)
    currency: str = "INR"
    category: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    is_subscription: bool = False
    is_addon: bool = False


class UserIntent(BaseModel):
    """Natural-language shopping instruction converted into structured constraints."""

    instruction: str
    product_name: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    max_price: Optional[float] = Field(default=None, ge=0)
    max_amount: Optional[float] = Field(default=None, ge=0)
    currency: str = "INR"
    categories: List[str] = Field(default_factory=list)
    allowed_categories: List[str] = Field(default_factory=list)
    allowed_merchants: List[str] = Field(default_factory=list)
    blocked_merchants: List[str] = Field(default_factory=list)
    allowed_colors: List[str] = Field(default_factory=list)
    allowed_sizes: List[str] = Field(default_factory=list)
    allow_subscription: bool = False
    allow_addons: bool = False
    daily_limit: Optional[int] = None
    session_limit: Optional[int] = None
    review_threshold: Optional[int] = None
    previous_approved_amounts: List[int] = Field(default_factory=list)
    policy_id: Optional[str] = None


class ProposedTransaction(BaseModel):
    """A cart or payment proposal from an AI buyer."""

    user_id: str
    items: List[CartItem] = Field(default_factory=list)
    total_amount: Optional[float] = None
    currency: str = "INR"
    merchant_id: str = "merchant_default"
    notes: Optional[str] = None
    transaction_id: Optional[str] = None


class PolicyDecision(BaseModel):
    """Final decision made by the deterministic policy engine."""

    decision: Literal["ALLOW", "ASK", "BLOCK"]
    reasons: List[str] = Field(default_factory=list)
    violated_rules: List[str] = Field(default_factory=list)
    evaluated_amount: int = 0
    cumulative_amount: int = 0
    remaining_limit: int = 0
    policy_id: str = ""
    transaction_id: str = ""
    reason: str = ""
    risk_score: int = Field(default=0, ge=0, le=100)
    flags: List[str] = Field(default_factory=list)
    requires_human_confirmation: bool = False


class ApprovalRecord(BaseModel):
    """Human review outcome for an ASK decision."""

    transaction_id: str
    original_decision: Literal["ASK"]
    human_decision: Literal["APPROVE", "REJECT"]
    reviewer: str
    note: Optional[str] = None
    timestamp: Optional[str] = None
