# 🛡️ Agent Leash
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

**📊 Project Presentation:**
[Download Agent Leash PPT](./AgentLeash.pptx)

---

## 🎯 The Problem

AI agents can increasingly purchase products and make financial decisions for users.

Natural-language instructions can be misunderstood, extended, or exploited. Without a policy layer, authorizing an AI agent can become a blank check.

**Common Risks**

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
Razorpay TEST MODE Order Flow
```

Every AI-proposed transaction is evaluated against structured constraints derived from the user's authorization.

### Decision Model

| Decision | Meaning |
|----------|---------|
| 🟢 **ALLOW** | Transaction fully matches the user's authorization |
| 🟡 **ASK** | Borderline case requiring explicit human review |
| 🔴 **BLOCK** | Transaction violates policy and is stopped before payment |

---

## ✅ Implemented Features

- FastAPI backend
- Gemini-based AI intent parsing
- Deterministic Policy Engine
- AI transaction simulator
- ALLOW / ASK / BLOCK decisions
- Maximum amount validation
- Allowed category validation
- Merchant allow/block rules
- Color and size matching
- Subscription restriction
- Add-on restriction
- Daily spending limits
- Session spending limits
- Aggregate/split transaction detection
- Fail-closed financial validation
- Currency validation
- Integer paise normalization
- Streamlit security dashboard
- Human approval workflow
- SQLite audit and approval persistence
- Five demo scenarios
- Razorpay TEST MODE order creation
- Automated testing
- Live Render deployment
- **Current test suite: 47 / 47 tests passing**

---

## 🧪 Demo Scenarios

| Scenario | AI Behavior | Result |
|----------|-------------|--------|
| `SAFE_PURCHASE` | Authorized purchase within all constraints | 🟢 ALLOW |
| `UNAUTHORIZED_ADDON` | AI adds an unauthorized warranty/accessory | 🔴 BLOCK |
| `UNAUTHORIZED_SUBSCRIPTION` | AI adds an unauthorized recurring subscription | 🔴 BLOCK |
| `OVER_LIMIT` | AI proposes a purchase above the maximum | 🔴 BLOCK |
| `AGGREGATE_SPLIT` | Transactions combine to exceed spending limits | 🔴 BLOCK |

---

## 🧾 Example Demo

**User Authorization**
> "Buy black running shoes, size 9, under ₹3000. No extras."

**Safe AI Proposal**

```
Black Running Shoes   ₹2,799
Category: Footwear
Color: Black
Size: 9
```

**Result:** 🟢 ALLOW
**Risk Score:** 10
**Violated Rules:** None

**Unauthorized Add-on Proposal**

```
Shoes                 ₹2,799
Extended Warranty       ₹499
Total                  ₹3,298
User Maximum           ₹3,000
```

**Result:** 🔴 BLOCK
**Risk Score:** 90

**Violations**
- Maximum amount exceeded
- Unauthorized category
- Unauthorized add-on

---

## 🙋 Human-in-the-Loop

For borderline transactions:

```
ASK
 ↓
Human Review
 ↓
APPROVE or REJECT
 ↓
SQLite Audit Record
```

An ASK decision is never silently converted to ALLOW.
An explicit human decision is required before the transaction can proceed.

---

## 💳 Razorpay TEST MODE

Razorpay integration is implemented for **TEST MODE**.

**Payment Flow**

```
ALLOW
  ↓
Razorpay TEST Order

ASK
  ↓
Human APPROVE
  ↓
Razorpay TEST Order

ASK
  ↓
Human REJECT
  ↓
No Order

BLOCK
  ↓
No Razorpay Order
```

The project does not process real payments. Razorpay is used only in TEST MODE for demonstration.

---

## 🛡️ Security by Design

**Deterministic Policy Enforcement**
The same input produces the same policy decision.

**Explainable Decisions**
Every decision includes the rules and reasons behind it.

**Fail-Closed Behavior**
Invalid financial values are rejected rather than guessed.

**Human Approval**
Borderline transactions wait for explicit human confirmation.

**No Payment for Blocked Transactions**
A BLOCK decision prevents Razorpay order creation.

**Auditability**
Policy decisions and human approvals are persisted in SQLite.

---

## 🧰 Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Backend | FastAPI |
| Language | Python |
| AI | Gemini |
| Validation | Pydantic |
| Database | SQLite |
| Payments | Razorpay TEST MODE |
| Testing | Python `unittest` |
| Deployment | Render |

---

## 🧪 Testing

The project includes an automated test suite covering:

- Policy engine
- AI parser
- Agent simulator
- Approval workflow
- Razorpay integration

**47 / 47 automated tests passing**

---

## 📁 Project Structure

```
agent-leash/
│
├── backend/
│   ├── __init__.py
│   ├── agent_simulator.py
│   ├── ai_parser.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── policy_engine.py
│   └── razorpay_service.py
│
├── frontend/
│   └── app.py
│
├── tests/
│   ├── __init__.py
│   ├── test_agent_simulator.py
│   ├── test_ai_parser.py
│   ├── test_approval_flow.py
│   ├── test_policy_engine.py
│   └── test_razorpay_integration.py
│
├── AgentLeash.pptx
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 💻 Local Setup

**1. Clone the repository**

```bash
git clone https://github.com/boggulanandu-art/agent-leash.git
cd agent-leash
```

**2. Create a virtual environment**

```bash
python -m venv .venv
```

**3. Activate the environment**

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

**4. Install dependencies**

```bash
pip install -r requirements.txt
```

**5. Start the Backend**

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**6. Start the Dashboard**

```bash
streamlit run frontend/app.py --server.port 8501
```

---

## 🔑 Environment Variables

**Never commit API keys or secrets to GitHub.**

Use environment variables for:

```
GEMINI_API_KEY
RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET
```

Razorpay credentials used for the demo must be **TEST MODE** credentials.

---

## 📌 Current Status

**Completed**

- ✅ Deterministic policy engine
- ✅ AI intent parsing
- ✅ Five demo scenarios
- ✅ Streamlit dashboard
- ✅ Human approval workflow
- ✅ SQLite audit persistence
- ✅ Razorpay TEST MODE order flow
- ✅ 47 / 47 automated tests passing
- ✅ GitHub repository
- ✅ Live Render deployment
- ✅ Hackathon presentation

**Future Improvements**

- Production payment integrations
- Stronger audit and analytics UI
- More AI-agent integrations
- Additional policy controls
- Production-grade security hardening

---

## 📊 Project Presentation

The final hackathon presentation is included in the repository:

📥 [Download Agent Leash Presentation](./AgentLeash.pptx)

---

## ⚠️ Disclaimer

This project was developed as a hackathon prototype.

Razorpay integration is **TEST MODE only** and no real payments are processed.

Do not use this codebase in production without a full security and compliance review.

---
🏆 Hackathon Project

"AI can act fast. Agent Leash makes sure it acts within the user's authority."

## 🏆 Hackathon Project

> "AI can act fast. Agent Leash makes sure it acts within the user's authority."
