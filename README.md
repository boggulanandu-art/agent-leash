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

### Common Risks

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
