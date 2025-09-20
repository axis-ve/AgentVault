# VaultPilot MCP Control Plane — Product Requirements Document

## 1. Vision & Context

- **Product name:** VaultPilot (formerly AgentVault MCP)
- **Mission:** Deliver a turnkey control plane that lets AI and automation teams securely operate on-chain agents. Customers provision wallets, enforce guardrails, orchestrate DeFi strategies, and connect MCP-enabled assistants without touching low-level Web3 plumbing.
- **Why now:** Agentic workflows are proliferating faster than security and compliance expertise. Teams need audited wallet infrastructure, spend limits, and programmable strategies that plug straight into LLM tooling.
- **Differentiation:** MCP-native interface, opinionated security (encrypted stores, confirmation codes), rich strategy/DeFi library, and the ability to surface dashboards & UI artifacts instantly.

## 2. Target Customers & Use Cases

| Segment | Buyer Persona | Key Jobs-to-be-Done |
| --- | --- | --- |
| AI agent startups | Founders/tech leads | Launch on-chain agents quickly, avoid wallet security debt, demo workflows with tip-jars/dashboards |
| Automation agencies | Ops/solutions engineers | Manage multiple client wallets, run conditional payouts/DCA, share reporting |
| Web3 product teams | Program managers | Prototype DeFi flows, integrate with internal assistants, satisfy compliance reviews |

Top use cases:
1. **Agent wallet provisioning** with spend ceilings, approval codes, faucet access.
2. **Recurring strategy automation** (DCA, gas-based sends, micro-tipping, Aave supply) visible to both humans and agents.
3. **DeFi execution** (Uniswap Universal Router, Permit2, token inspection) with dry-run tooling for deterministic flows.
4. **UI/asset generation** (tip jars, dashboards) for community or stakeholder transparency.

## 3. Success Metrics

- **Activation:** 80% of new tenants create a wallet and run at least one MPC strategy within 48 hours.
- **Security:** 0 unresolved incidents of private key leakage; 100% transactions fall within configured policies.
- **Reliability:** 99.5% MCP server availability with auto-failover RPCs; <1% failed strategy ticks (excluding on-chain reverts).
- **Revenue:** Achieve $25k ARR within first three months of GA through SaaS tiers + enterprise pilot.

## 4. High-Level Architecture (Goal State)

1. **VaultPilot Control Plane (SaaS option)**
   - Multi-tenant API + auth (JWT/OAuth) with RBAC.
   - Managed MCP endpoints per tenant (Kubernetes/containers) connected to secure key vault/HSM.
   - Postgres-backed persistence for wallets, strategies, events, billing metrics.
   - Observability stack (Prometheus/Grafana, structured logging pipeline).

2. **VaultPilot Edge (Self-host)**
   - Docker Compose bundle: MCP server, Postgres, Redis (celery/queue), admin UI.
   - Pluggable key encryption modules (Fernet, AWS KMS, Hashicorp Vault).

3. **Agent Connectors**
   - SDK snippets / templates for Claude Desktop, Cursor, LangGraph, custom Python/TypeScript.
   - Webhook + REST APIs for event notifications and off-protocol management tasks.

## 5. Phased Delivery Plan

### Phase 1 – MVP Packaging (Weeks 0–6)

**Goals:** Migrate persistence to SQL, ship deployable bundle, deliver admin experience, and formalize policy controls.

| Workstream | Key Deliverables | Technical Direction |
| --- | --- | --- |
| Persisted stores | Replace JSON with SQLAlchemy/async engine (SQLite for dev, Postgres in prod). Migrate `AgentWalletManager` & `StrategyManager`. Provide migration script for existing JSON stores. | Introduce `db` module, alembic migrations, and repository pattern. Ensure encryption keys remain Fernet-wrapped before hitting DB. |
| Deployment packaging | Dockerfile + docker-compose for MCP server, Postgres, worker (for async tasks), and admin UI. | Build multi-stage image pulling from `pyproject.toml`. Parameterize via `.env`. Add healthchecks & log shipping. |
| Admin dashboard | React (Next.js or Vite) UI served via `/admin`. Read-only for MVP: wallet list, balances, strategies, transaction log. | Expose REST endpoints (FastAPI/Starlette) co-located with MCP server to avoid separate runtime. Use `structlog` events as source for activity feed. |
| Policy/guardrails | Configurable rate limits, per-wallet spend thresholds, IP allowlists, event audit log. | Add middleware around MCP tool invocations to enforce quotas. Persist events in DB. Formalize `MCP metadata` tagging for side-effect tools. |
| Documentation | Installation guide, admin walkthrough, agent integration quick-start, architecture diagram. | Host docs in `docs/` + MkDocs site. |

### Phase 2 – SaaS Control Plane (Weeks 6–16)

| Workstream | Deliverables | Technical Direction |
| --- | --- | --- |
| Multi-tenancy | Tenant-aware DB schema, auth, RBAC, invitation system, API keys. | Introduce user/tenant tables, `@tenant_scoped` decorators, per-tenant encryption key management. JWT auth service. |
| Managed MCP endpoints | Provision per-tenant containers via orchestrator (Kubernetes/ECS). Auto-scale, health monitoring. | Implement control-plane service handing lifecycle (create/update/destroy). Use Helm charts/Terraform modules. |
| Billing & metering | Usage tracking (transactions, strategies, CPU time), Stripe integration with metered billing and plan enforcement. | Background workers aggregate metrics; expose to billing service daily. Implement plan entitlements in policy layer. |
| Notifications | Slack/email/webhook alerts for approval requests, failures, spend breaches. | Event bus + subscription preferences. Use Celery or AWS EventBridge for fan-out. |
| Support tooling | Audit trail viewer, impersonation, support logs. | Build admin-only UI & API endpoints. |

### Phase 3 – Differentiators (Post-GA)

| Workstream | Deliverables | Technical Direction |
| --- | --- | --- |
| Strategy composer | Visual builder for chained actions, scheduling, branching. | Graph-based DSL persisted to DB; runtime compiles to asynchronous jobs using existing primitives. |
| DeFi marketplace | Curated strategy templates (yield, swaps, staking). Integration with external protocols. | Extend `DeFiManager` with plugin architecture; add simulation/test harness. |
| Compliance suite | Chain analytics integration, risk scoring, exportable audits, SOX-ready logging. | Integrate with Chainalysis/Alchemy Monitor APIs, create compliance reports. |
| Premium integrations | Hooks for Fireblocks, Ledger Enterprise, Chainlink keeper scheduling. | Adapter interfaces, feature flags per plan. |

## 6. Detailed Technical Backlog (Phase 1)

1. **Storage Layer Migration**
   - Introduce `database/engine.py` with async SQLAlchemy + Alembic migrations.
   - Create tables: `wallets`, `wallet_keys`, `strategies`, `strategy_runs`, `mcp_events`, `users` (stub for future auth).
   - Update `AgentWalletManager` to CRUD via repositories; encrypt private keys before persisting.
   - Build migration script to import existing JSON stores (one-time CLI command).

2. **MCP Middleware + Policy Engine**
   - Wrap tool handlers with decorator capturing tool metadata, enforcing rate limits, and logging outcomes.
   - Add config file structure (`vaultpilot.yml`) for policies (per wallet spend limit, confirmation code, allowed tools, IP restrictions).
   - Emit structured events for every call to `mcp_events` table.

3. **REST API Layer**
   - Add FastAPI app inside `server.py` runtime for admin/dashboard endpoints (wallet listing, balances, transactions, strategies, events, config).
   - Provide OpenAPI schema for UI + external integrations.

4. **Admin UI**
   - Scaffold `ui/admin/` React app (TypeScript) with views: overview, wallets, strategies, events, settings.
   - Build API client, authentication (MVP: API token), design system aligned with brand.

5. **Containerization & DevOps**
   - Write Dockerfile with multi-stage build (builder, runtime) for MCP server + API.
   - Compose file adding Postgres, Redis (for background jobs), and the admin UI.
   - GitHub Actions workflow for building container, running tests, pushing artifacts.

6. **Observability**
   - Integrate Prometheus metrics using `prometheus_client` (RPC health, strategy counts, tool latency).
   - Provide Grafana dashboard JSON templates.

7. **Docs & Enablement**
   - Author Quick Start (Docker + manual install), Policy configuration guide, Agent connector recipes.
   - Record architecture diagram (Mermaid/Excalidraw) and include in docs site.

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| SQL migration introduces data loss | High | Provide backup tooling, dry-run migration, and extensive tests. |
| Security posture regression when centralizing keys | Critical | Keep encryption at rest per wallet, evaluate HSM/KMS integration early, penetration tests. |
| DeFi dependency churn | Medium | Pin `web3-ethereum-defi`, create nightly smoke tests hitting testnets. |
| MCP protocol changes | Medium | Maintain compatibility matrix, participate in MCP community updates. |
| Resource cost for hosted variant | Medium | Implement autoscaling & per-tenant limits, track margin. |

## 8. Open Questions / Follow-Ups

1. Target infrastructure for hosted SaaS (AWS ECS vs. GKE vs. Fly.io) — require cost/ops analysis.
2. Decision on long-term KMS solution (AWS KMS, Hashicorp Vault, custom HSM?).
3. Licensing model for on-prem (GPL/commercial dual-license?).
4. Scope of compliance requirements for early enterprise buyers (SOC2, ISO?).

## 9. Timeline & Milestones (draft)

- **Week 0:** Kickoff, finalize architecture decisions, set up project tracking (Linear/Jira).
- **Week 2:** Database migration code complete; JSON importer functional.
- **Week 4:** Policy engine + REST API live behind feature flag; Docker compose running locally.
- **Week 6:** Admin UI alpha, documentation ready, Phase 1 MVP release candidate.
- **Week 10:** Multi-tenancy beta, billing integration started.
- **Week 16:** SaaS GA, begin Phase 3 enhancements.

## 10. Appendices

- **Glossary:**
  - *MCP:* Model Context Protocol, standard for tool invocation between LLMs and services.
  - *Strategy:* A persisted workflow (e.g., DCA) executed periodically with guardrails.
  - *Policy:* Rules governing tool usage, spend limits, and approvals.
- **Reference Materials:**
  - Existing docs: `docs/mcp-compliance.md`, `docs/user-onboarding.md`, `docs/prompt-pack.md`.
  - Sample agent connectors from `docs/mcp-integration-examples.md`.

