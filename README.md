# 🛡️ Agent Leash

**Security Layer for AI-Powered Transactions**

> AI can propose. Agent Leash decides.

Agent Leash is an independent security and authorization layer for AI-powered commerce. AI agents can understand natural-language instructions and propose purchases — but the AI should never be the final authority over money.

Agent Leash converts user authorization into structured constraints, evaluates every proposed transaction with a deterministic policy engine, and enforces one of three outcomes:

**🟢 ALLOW · 🟡 ASK · 🔴 BLOCK**

Only transactions that satisfy the required authorization can reach the Razorpay **TEST MODE** payment flow.

---

## 📋 Table of Contents

- [Demo Video](#-demo-video)
- [The Problem](#-the-problem)
- [The Solution](#-the-solution)
- [Policy Engine](#-policy-engine)
- [Example Walkthroughs](#-example-safe-purchase)
- [Human-in-the-Loop](#-human-in-the-loop)
- [Razorpay Test Mode](#-razorpay-test-mode)
- [Demo Scenarios](#-demo-scenarios)
- [Risk Scoring & Audit Trail](#-risk-scoring--audit-trail)
- [AI Layer](#-ai-layer)
- [Dashboard](#️-dashboard)
- [Security by Design](#️-security-by-design)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Local Setup](#-local-setup)
- [Environment Variables](#-environment-variables)
- [Run Locally](#️-run-locally)
- [API Endpoints](#-api-endpoints)
- [Testing](#-testing)
- [Project Status](#-project-status)
- [Disclaimer](#️-disclaimer)
- [Author](#-author)
- [Core Philosophy](#-core-philosophy)

---

## 🎥 Demo Video

Watch the complete Agent Leash demonstration:

▶️ **[Watch the Agent Leash Demo](https://youtu.be/9O6ycQoXRDk)**

The demo covers:

- Natural-language user authorization
- AI intent parsing
- AI Buyer proposal
- Deterministic policy evaluation
- ALLOW / ASK / BLOCK decisions
- Human approval workflow
- Risk scoring
- Audit trail
- Razorpay TEST MODE order flow
- Five security scenarios

---

## 🎯 The Problem

AI shopping agents can increasingly understand user requests and initiate transactions. This creates a new security risk: an AI agent may misunderstand an instruction, exceed a spending limit, or add something the user never authorized.

**Example authorization:**

```
Buy black running shoes, size 9, under ₹3000. No extras.
```

Without an independent policy layer, an AI agent could potentially:

- Misinterpret user instructions
- Exceed the authorized spending limit
- Add unauthorized products or warranties
- Add unwanted subscriptions
- Split transactions to bypass limits

Agent Leash provides an independent authorization boundary between the AI agent and payment execution.

---

## 💡 The Solution

Agent Leash separates AI decision-making from financial authorization.

```
User
 ↓
Natural-Language Authorization
 ↓
AI Intent Parser
 ↓
Structured UserIntent
 ↓
AI Buyer
 ↓
Proposed Transaction
 ↓
Agent Leash Policy Engine
 ↓
┌──────────┬──────────┬──────────┐
│  ALLOW   │   ASK    │  BLOCK   │
└────┬─────┴────┬─────┴────┬─────┘
     │           │          │
     │           ▼          │
     │      Human Review    │
     │           │          │
     └─────┬─────┘          │
           ▼                ▼
   Razorpay TEST       No Payment
       Order
```

**The AI proposes the transaction. The Policy Engine authorizes it.**

---

## 🔐 Policy Engine

The Policy Engine is deterministic and independently evaluates every proposed transaction. It checks:

- Maximum transaction amount
- Allowed categories
- Merchant restrictions
- Product attributes (color, size)
- Subscription permission
- Add-on permission
- Daily and session spending limits
- Aggregate transaction limits
- Split-transaction detection

**The AI cannot modify or override these security constraints.**

### Decision Model

| Decision | Meaning |
|---|---|
| 🟢 **ALLOW** | The transaction satisfies the user's authorization and can proceed. |
| 🟡 **ASK** | The transaction pauses for explicit human review. |
| 🔴 **BLOCK** | The transaction violates a mandatory policy and payment execution is prevented. |

---

## 🛒 Example: User Authorization

```
Buy black running shoes, size 9, under ₹3000. No extras.
```

Agent Leash extracts:

```
Category:       footwear
Color:          black
Size:           9
Maximum Amount: ₹3000
Add-ons:        Not Allowed
Subscriptions:  Not Allowed
```

## ✅ Example: Safe Purchase

**AI Buyer Proposal**

```
Product:  Black Running Shoes
Price:    ₹2799
Color:    Black
Size:     9
Category: Footwear
```

**Policy Evaluation**

```
Price ₹2799 ≤ User Limit ₹3000     ✓
Category matches                    ✓
Color matches                       ✓
Size matches                        ✓
No unauthorized add-ons             ✓
No unauthorized subscription        ✓
```

**Result**

```
Decision:    ALLOW
Risk Score:  10
Violations:  None
```

The transaction proceeds to the Razorpay TEST order flow.

## 🚨 Example: Unauthorized Add-on

```
Black Running Shoes       ₹2,799
Extended Warranty           ₹499
--------------------------------
Total                     ₹3,298

User Maximum               ₹3,000
```

Agent Leash detects:

- ❌ Maximum amount exceeded
- ❌ Unauthorized category
- ❌ Unauthorized add-on

**Result**

```
Decision:   BLOCK
Risk Score: 90
```

No Razorpay order is created for the blocked transaction.

---

## 🙋 Human-in-the-Loop

Transactions requiring additional review follow:

```
ASK
 ↓
Human Review
 ↓
APPROVE / REJECT
 ↓
SQLite Audit Record
```

An **ASK** decision is never silently converted into **ALLOW**. An explicit human decision is required before the transaction can proceed.

---

## 💳 Razorpay TEST MODE

Agent Leash integrates with Razorpay in TEST MODE:

- **ALLOW** → Razorpay TEST Order
- **ASK** → Human APPROVE → Razorpay TEST Order
- **ASK** → Human REJECT → No Order
- **BLOCK** → No Razorpay Order

**No real payments are processed.**

---

## 🧪 Demo Scenarios

| Scenario | Expected Result | Purpose |
|---|---|---|
| `SAFE_PURCHASE` | 🟢 ALLOW | Valid purchase within authorization |
| `UNAUTHORIZED_ADDON` | 🔴 BLOCK | Unauthorized warranty/add-on |
| `UNAUTHORIZED_SUBSCRIPTION` | 🔴 BLOCK | Unauthorized subscription |
| `OVER_LIMIT` | 🔴 BLOCK | Spending-limit violation |
| `AGGREGATE_SPLIT` | 🔴 BLOCK | Split transactions exceeding limits |

Available through:

```
GET /demo/scenarios
```

---

## 📊 Risk Scoring & Audit Trail

Agent Leash provides a risk score alongside the policy decision and stores transaction/approval information in SQLite.

The audit trail records:

- User request
- Proposed transaction
- Policy decision
- Risk score
- Violated rules
- Human approval/rejection
- Transaction state

---

## 🤖 AI Layer

Agent Leash currently uses **OpenRouter** for AI-powered intent parsing and AI Buyer functionality.

```
AI Provider: OpenRouter
Model:       openrouter/free
Client:      OpenAI-compatible API
```

```
Natural Language
       ↓
   OpenRouter
       ↓
Structured Intent
       ↓
   AI Proposal
       ↓
Deterministic Policy Engine
       ↓
ALLOW / ASK / BLOCK
```

The AI understands the request and proposes a transaction. **It does not decide whether money is authorized.**

---

## 🖥️ Dashboard

The Streamlit dashboard provides:

- Current security status
- Policy enforcement
- Current risk
- AI Buyer proposals
- ALLOW / ASK / BLOCK decisions
- Human approval workflow
- Demo scenarios
- Audit trail
- Razorpay TEST transaction status

---

## 🛡️ Security by Design

- **Deterministic enforcement** — explicit policy rules control authorization.
- **Explainable decisions** — decisions include reasons and violated rules.
- **Fail-closed behavior** — invalid financial values are rejected rather than guessed.
- **Human approval** — transactions requiring review wait for explicit action.
- **No payment for BLOCKED transactions** — blocked transactions cannot create Razorpay orders.
- **Auditability** — decisions and approvals are persisted in SQLite.
- **Separation of responsibilities** — AI proposes, policy authorizes, payment executes.

---

## 🧰 Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| Language | Python |
| AI Provider | OpenRouter |
| AI Model | openrouter/free |
| Data Validation | Pydantic |
| Database | SQLite |
| Payments | Razorpay TEST MODE |
| Testing | pytest |

---

## 📁 Project Structure

```
agent-leash/
├── backend/
│   ├── __init__.py
│   ├── agent_simulator.py
│   ├── ai_parser.py
│   ├── ai_buyer.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── policy_engine.py
│   └── razorpay_service.py
├── frontend/
│   └── app.py
├── tests/
│   ├── __init__.py
│   ├── test_agent_simulator.py
│   ├── test_ai_parser.py
│   ├── test_ai_buyer.py
│   ├── test_approval_flow.py
│   ├── test_ask_demo.py
│   ├── test_ask_presentation.py
│   ├── test_audit_trail.py
│   ├── test_policy_engine.py
│   └── test_razorpay_integration.py
├── AgentLeash.pptx
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 💻 Local Setup

### 1. Clone

```bash
git clone https://github.com/boggulanandu-art/agent-leash.git
cd agent-leash
```

### 2. Create virtual environment

```bash
python -m venv .venv
```

### 3. Activate

**Windows:**

```bash
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_openrouter_api_key

RAZORPAY_KEY_ID=your_razorpay_test_key_id
RAZORPAY_KEY_SECRET=your_razorpay_test_key_secret
```

> ⚠️ Use Razorpay **TEST MODE** credentials only. Never commit API keys or secrets to GitHub.

---

## ▶️ Run Locally

### Backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: `http://127.0.0.1:8000`

### Dashboard

Open a second terminal:

```bash
streamlit run frontend/app.py --server.port 8501
```

Dashboard runs at: `http://localhost:8501`

---

## 🔌 API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Backend health check |
| `POST` | `/parse-intent` | Parse natural-language authorization |
| `POST` | `/agent/buy` | Run AI Buyer + policy evaluation |
| `POST` | `/approval` | Record human approval/rejection |
| `POST` | `/transactions/{transaction_id}/order` | Create Razorpay TEST order after authorization |
| `GET` | `/demo/scenarios` | Get deterministic demo scenarios |

---

## 🧪 Testing

Run the full test suite:

```bash
pytest -q
```

The suite covers:

- Policy Engine
- AI Parser
- AI Buyer
- Agent Simulator
- Approval workflow
- ASK workflow
- Audit trail
- Razorpay integration

---

## 📌 Project Status

### Completed

- ✅ Deterministic Policy Engine
- ✅ AI intent parsing
- ✅ OpenRouter AI Buyer
- ✅ ALLOW / ASK / BLOCK decisions
- ✅ Risk scoring
- ✅ Five demo scenarios
- ✅ Human approval workflow
- ✅ SQLite audit persistence
- ✅ Razorpay TEST MODE order flow
- ✅ Streamlit dashboard
- ✅ Automated test suite
- ✅ Demo presentation
- ✅ Demo video

### Future Improvements

- Production payment integrations
- Stronger audit and analytics UI
- Additional AI-agent integrations
- More advanced policy controls
- Production-grade security hardening

---

## 🏆 Razorpay Buildathon

Agent Leash is a hackathon prototype focused on making AI-powered commerce safer through explicit user authorization and independent policy enforcement.

> AI can act fast. Agent Leash makes sure it acts within the user's authority.

---

## ⚠️ Disclaimer

Agent Leash is a **hackathon prototype**.

- Razorpay integration uses **TEST MODE only** and does not process real payments.
- Do not use this codebase in production without a complete security, compliance, privacy, and payment-integration review.

---

## 👩‍💻 Author

**Nandini Boggula**

GitHub: [github.com/boggulanandu-art/agent-leash](https://github.com/boggulanandu-art/agent-leash)

---

## ⭐ Core Philosophy

```
        AI can propose
              ↓
       Agent Leash checks
              ↓
    ┌─────────┼─────────┐
    ↓         ↓         ↓
  ALLOW      ASK      BLOCK
    ↓         ↓         ↓
 Payment   Human     No Payment
           Review
```

**AI can propose. Agent Leash decides.**
