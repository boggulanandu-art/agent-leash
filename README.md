# Agent Leash
## Security Layer for AI-Powered Transactions

Agent Leash is a merchant-side security layer for AI-agent commerce.

AI agents can shop and make financial decisions on behalf of users. Agent Leash ensures that AI agents never act beyond the user's authorization.

> **AI interprets intent. Deterministic policy code authorizes money.**

---

## 🚀 Live Demo

**Dashboard:**
https://agent-leash-dashboard.onrender.com

**GitHub Repository:**
https://github.com/boggulanandu-art/agent-leash

---

## 🎯 The Problem

AI agents are increasingly capable of purchasing products and making financial decisions for users.

Natural-language instructions can be misunderstood, extended, or exploited. Without a policy layer, giving an AI agent authorization can effectively become giving it a blank check.

Common risks include:

- Misread instructions
- Unauthorized add-ons
- Hidden subscriptions
- Purchases exceeding spending limits
- Split transactions used to bypass limits

---

## 💡 The Solution

Agent Leash creates a **deterministic boundary between AI intent and money**.

```text
User
  ↓
Natural-Language Authorization
  ↓
AI Intent Parser (Gemini)
  ↓
Structured Authorization
  ↓
AI Agent Proposal
  ↓
Agent Leash Policy Engine
  ↓
┌─────────┬─────────┬─────────┐
│  ALLOW  │   ASK   │  BLOCK  │
└─────────┴─────────┴─────────┘
  ↓
Human Approval (if ASK)
  ↓
Razorpay TEST MODE Transaction Flow
```

Every AI-proposed transaction is evaluated against structured constraints derived from the user's own words, and receives exactly one of three outcomes:

| Decision | Meaning |
|----------|---------|
| 🟢 **ALLOW** | Transaction fully matches the user's authorization. Executes. |
| 🟡 **ASK** | Ambiguous or borderline case. Held for human review before anything happens. |
| 🔴 **BLOCK** | Violates one or more policy rules. Stopped before execution — no payment. |

---

## ✅ Implemented Features

- FastAPI backend
- AI intent parser using Gemini
- Deterministic Policy Engine
- AI transaction simulator
- ALLOW / ASK / BLOCK decisions
- Maximum transaction amount validation
- Allowed category validation
- Merchant allow/block validation
- Color/size attribute matching
- Subscription restriction
- Add-on restriction
- Daily spending limit
- Session spending limit
- Transaction splitting detection
- Fail-closed validation for invalid financial values
- Currency validation
- Integer paise normalization to avoid floating-point issues
- Streamlit dashboard
- Human approval workflow for ASK decisions
- SQLite approval/audit persistence
- Five demo scenarios
- Automated testing
- **Current test suite: 37 tests passing**

---

## 🧪 Demo Scenarios

| Scenario | AI Behavior | Result |
|----------|-------------|--------|
| `SAFE_PURCHASE` | Authorized purchase, within all constraints | 🟢 ALLOW |
| `UNAUTHORIZED_ADDON` | AI adds an unauthorized warranty / accessory | 🔴 BLOCK |
| `UNAUTHORIZED_SUBSCRIPTION` | AI adds a recurring subscription | 🔴 BLOCK |
| `OVER_LIMIT` | AI proposes a purchase above the user's maximum | 🔴 BLOCK |
| `AGGREGATE_SPLIT` | Reasonable transactions combine to exceed daily/session limits | 🔴 BLOCK |

### Example: Real Demo Walkthrough

**User authorization:**
> "Buy black running shoes, size 9, under ₹3000. No extras."

**Safe AI proposal**

```
Black Running Shoes   ₹2,799
Category: Footwear
Color: Black
Size: 9
```
→ **ALLOW** · Risk score: 10 · No violated rules

**Unauthorized add-on proposal**

```
Shoes                 ₹2,799
Extended Warranty       ₹499
Total                  ₹3,298
User Maximum           ₹3,000
```
→ **BLOCK** · Risk score: 90
Violations: maximum amount exceeded · unauthorized category · unauthorized add-on

---

## 🙋 Human-in-the-Loop (ASK Workflow)

The Policy Engine already supports ASK for borderline cases:

```
ASK → Human Review → APPROVE or REJECT
```

- Approval/rejection decisions are stored in SQLite for audit.
- The current workflow does **NOT** automatically turn ASK into ALLOW — every ASK transaction waits for an explicit human decision.

---

## 💳 Payments — Razorpay (TEST MODE)

Razorpay integration is the **next implementation stage**, not a completed feature.

Current state:

- Razorpay service skeleton exists
- Razorpay TEST credentials are configured locally
- Official Razorpay Python SDK is being integrated
- Test Mode only — **no real/live payments**

Target architecture:

```
ALLOW  → Razorpay TEST order
ASK    → Human APPROVE → Razorpay TEST order
ASK    → Human REJECT  → No order
BLOCK  → No Razorpay order
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Backend | FastAPI |
| Language | Python |
| AI | Gemini |
| Validation | Pydantic |
| Database | SQLite |
| Payments | Razorpay (TEST MODE) |
| Testing | Python `unittest` |

---

## 🔒 Why Agent Leash

- **Deterministic policy enforcement** — no probabilistic judgment calls; the same input always gives the same decision.
- **Explainable decisions** — every ALLOW / ASK / BLOCK comes with the exact rule that triggered it.
- **Fail-closed behavior** — invalid or malformed financial values are rejected, not guessed at.
- **Human approval** — borderline transactions always wait for a real person to decide.
- **No payment for blocked transactions** — a BLOCK verdict means no Razorpay order is ever created.
- **Full auditability** — every decision and approval is persisted in SQLite for review.

---

## 📌 Current Status

**Working:**
- Core policy engine complete
- 5 demo scenarios working
- Streamlit dashboard working
- Human approval workflow working
- 37 / 37 automated tests passing

**Next:**
- Razorpay TEST MODE integration
- Payment / order flow
- Stronger audit UI
- Final deployment
- Production-grade integrations

---

## ⚠️ Disclaimer

This project is under active development for a hackathon submission. Razorpay integration is in **TEST MODE only** — no real payments are processed. Do not use this codebase in production without a full security review.

---

## 📄 License

Add your preferred license here (e.g. MIT).
