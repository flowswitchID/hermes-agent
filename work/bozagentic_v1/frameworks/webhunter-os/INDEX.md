---
name: webhunter-os-index
description: Quick lookup index for the webhunter-os mega-skill. Maps common web/API/cloud vulnerability classes, technology stacks, and process questions to specific files in the knowledge base.
---

# WebHunter OS — Master Index

Quick navigation for the 173 files in `webhunter-os/`. Use this as a router when you need to find specific information fast.

## How to Use This Index

1. **Identify your question type** below
2. **Jump to the relevant section**
3. **Load the specific file(s)** for details

---

## 🎯 Quick Routes

### "I'm starting a new web audit"
1. → `workflow/Phase1_Reconnaissance_Intelligence.md`
2. → `workflow/Phase2_Attack_Surface_Mapping.md`
3. → `workflow/Phase3_Threat_Modeling.md`
4. → `playbook-core/` (per vuln class workflow)

### "I'm hunting a specific bug class"
→ See [Vulnerability Classes](#-vulnerability-classes) below

### "I'm auditing a specific tech stack"
→ See [Tech Stacks](#-tech-stacks) below

### "I want to learn from past exploits"
→ See [Exploit Knowledge Base](#-exploit-knowledge-base) below

### "I'm writing a report"
1. → `workflow/Phase8_Reporting_Remediation.md`
2. → `reporting-quality/` (automation)
3. → `orchestrator-core/Report_Generator.md`

### "I need to validate a finding"
1. → `workflow/Phase6_Exploit_Validation_Impact.md`
2. → `exploit-kb-*` (similar cases)
3. → `decision-engine/Confidence_Scoring.md`

---

## 🐛 Vulnerability Classes

### IDOR / BOLA / BFLA
- `phase1-auth/IDOR.md`
- `phase1-auth/Broken_Access_Control.md`
- `exploit-kb-1/Authorization/IDOR_Knowledge.md`
- `exploit-kb-3/API_Exposure/Mass_Assignment_Knowledge.md`
- `playbook-core/Authorization/Access_Control_Playbook.md`

### Broken Authentication
- `phase1-auth/Broken_Authentication.md`
- `playbook-core/Authentication/Login_Testing_Playbook.md`

### JWT Vulnerabilities
- `phase1-auth/JWT_Weaknesses.md`
- `exploit-kb-1/Authentication/JWT_Token_Abuse.md`

### OAuth / OIDC
- (in `phase1-auth/` & `exploit-kb-1/Authentication/`)
- `playbook-core/Authentication/`

### Session Management
- `phase3-session-api/` (session-related files)
- `playbook-core/Authentication/Login_Testing_Playbook.md`

### MFA Bypass
- `phase1-auth/` (Broken Authentication covers)
- `playbook-core/Authentication/`

### SQL Injection
- `phase2-injection/04_Injection/SQL_Injection.md`
- `exploit-kb-1/Injection/SQLi_Knowledge.md`
- `playbook-core/Injection/Injection_Playbook.md`

### SSTI (Server-Side Template Injection)
- `phase2-injection/04_Injection/Server_Side_Template_Injection.md`
- `playbook-vuln/` (RCE playbook covers)

### Command Injection / RCE
- `phase2-injection/04_Injection/Command_Injection.md`
- `exploit-kb-2/Server_Side/RCE_Knowledge.md`
- `playbook-vuln/RCE/RCE_Playbook.md`

### XXE
- `phase2-injection/` (XML-related)
- `exploit-kb-2/Server_Side/`

### Mass Assignment
- `phase2-injection/03_Input_Validation/Mass_Assignment.md`
- `exploit-kb-3/API_Exposure/Mass_Assignment_Knowledge.md`

### SSRF
- `exploit-kb-1/Injection/SSRF_Knowledge.md`
- `playbook-vuln/Server_Side/`

### CSRF
- `phase3-session-api/07_API_Security/CSRF.md`
- `exploit-kb-2/Browser_Security/CSRF_Knowledge.md`

### CORS Misconfig
- `phase3-session-api/07_API_Security/CORS_CSP.md`
- `exploit-kb-2/Browser_Security/CORS_Knowledge.md`

### XSS (Reflected, Stored, DOM)
- `phase4-advanced/12_Client_Side/` (XSS patterns)
- `exploit-kb-2/Browser_Security/`

### WebSocket Hijacking
- `phase4-advanced/12_Client_Side/WebSocket_Security.md` (or similar)
- `exploit-kb-2/Browser_Security/`

### HTTP Request Smuggling
- `phase4-advanced/` (advanced patterns)

### Path Traversal / LFI / RFI
- `phase4-advanced/` (server-side patterns)
- `exploit-kb-2/Server_Side/Path_Traversal_Knowledge.md`
- `playbook-vuln/Path_Traversal/Path_Traversal_Playbook.md`

### File Upload
- `playbook-vuln/File_Upload/File_Upload_Playbook.md`

### Deserialization
- `playbook-vuln/Deserialization/Deserialization_Playbook.md`

### GraphQL
- `phase3-session-api/07_API_Security/GraphQL_Security.md`
- `exploit-kb-3/API_Exposure/` (GraphQL knowledge)

### REST API
- `phase3-session-api/07_API_Security/REST_API_Security.md`
- `exploit-kb-3/API_Exposure/`
- `playbook-core/API/API_Audit_Playbook.md`

### Rate Limit Bypass
- `exploit-kb-3/API_Exposure/API_Rate_Limiting.md`

### Business Logic / Workflow Bypass
- `phase4-advanced/16_Business_Logic/Workflow_Bypass.md`
- `exploit-kb-5/AI_Reasoning/Multi_Step_Attack_Planning.md`

### DoS / Resource Exhaustion
- `phase4-advanced/14_Denial_of_Service/Resource_Exhaustion.md`

### Information Disclosure
- `phase4-advanced/13_Information_Disclosure/Information_Disclosure.md`
- `exploit-kb-2/Server_Side/`

### Security Misconfiguration
- `phase4-advanced/15_Security_Misconfiguration/Debug_Exposure.md`
- `playbook-cloud/Reverse_Proxy/Reverse_Proxy_Playbook.md`

---

## ☁️ Cloud & Infrastructure

### AWS
- `exploit-kb-4/Web_Infrastructure/Nginx_Apache_Knowledge.md` (covers AWS infra)
- `exploit-kb-4/IAM/Identity_Access_Knowledge.md`
- `exploit-kb-4/Secrets/Secrets_Management.md`
- `playbook-cloud/IAM/IAM_Playbook.md`
- `playbook-cloud/Secrets/Secrets_Management_Playbook.md`

### GCP / Azure
- `exploit-kb-4/` (general cloud)
- `playbook-cloud/`

### Cloud Metadata SSRF
- `exploit-kb-1/Injection/SSRF_Knowledge.md` (covers cloud metadata)

### Cloud Bucket Misconfig
- `exploit-kb-4/Web_Infrastructure/`
- `playbook-cloud/`

### CI/CD Pipeline
- `exploit-kb-4/CI_CD/CI_CD_Knowledge.md`
- `playbook-cloud/CI_CD/CI_CD_Playbook.md`

### Secrets Management
- `exploit-kb-4/Secrets/Secrets_Management.md`
- `playbook-cloud/Secrets/Secrets_Management_Playbook.md`

### Reverse Proxy Misconfig (Nginx/Apache)
- `exploit-kb-4/Web_Infrastructure/Nginx_Apache_Knowledge.md`
- `playbook-cloud/Reverse_Proxy/Reverse_Proxy_Playbook.md`

### IAM Misconfig
- `exploit-kb-4/IAM/Identity_Access_Knowledge.md`
- `playbook-cloud/IAM/IAM_Playbook.md`

---

## 🏗️ Tech Stacks

### SPA (React, Vue, Angular)
- `playbook-modern/SPA/SPA_Playbook.md`
- `phase3-session-api/07_API_Security/`

### Next.js / Next.js Apps
- `playbook-modern/SPA/` (Next.js covered in SPA)

### Microservices
- `playbook-modern/Microservices/Microservices_Playbook.md`

### Event-Driven Architecture
- `playbook-modern/Event_Driven/Event_Driven_Playbook.md`

### API Gateway
- `playbook-modern/API_Gateway/API_Gateway_Playbook.md`

### WebSocket Apps
- `phase4-advanced/12_Client_Side/`

---

## 💥 Exploit Knowledge Base

Each knowledge file documents how a vulnerability manifests in the wild, with detection heuristics and validation strategies.

### `exploit-kb-1/` (5 files)
- `Injection/SSRF_Knowledge.md`
- `Injection/SQLi_Knowledge.md`
- `Authorization/IDOR_Knowledge.md`
- `Authentication/JWT_Token_Abuse.md`
- `README.md`

### `exploit-kb-2/` (9 files)
- `Browser_Security/CORS_Knowledge.md`
- `Browser_Security/CSRF_Knowledge.md`
- `Server_Side/Path_Traversal_Knowledge.md`
- `Server_Side/RCE_Knowledge.md`
- (and 5 more server/browser knowledge files)

### `exploit-kb-3/` (10 files) — API & Modern Apps
- `API_Exposure/Shadow_API.md`
- `API_Exposure/API_Rate_Limiting.md`
- `API_Exposure/Excessive_Data_Exposure.md`
- `API_Exposure/Mass_Assignment_Knowledge.md`
- (and 6 more)

### `exploit-kb-4/` (11 files) — Cloud & Infrastructure
- `CI_CD/CI_CD_Knowledge.md`
- `Secrets/Secrets_Management.md`
- `IAM/Identity_Access_Knowledge.md`
- `Web_Infrastructure/Nginx_Apache_Knowledge.md`
- (and 7 more)

### `exploit-kb-5/` (9 files) — Exploit Chains
- `Impact_Escalation/Impact_Correlation.md`
- `AI_Reasoning/Multi_Step_Attack_Planning.md`
- `AI_Reasoning/Root_Cause_Correlation.md`
- `Case_Studies/High_Impact_Bug_Bounty_Patterns.md`
- (and 5 more reasoning files)

---

## 🏗️ Audit Phases (8-Phase Workflow)

The `workflow/` directory contains the master 8-phase methodology.

| Phase | File | Purpose |
|---|---|---|
| **Phase 1: Recon** | `workflow/Phase1_Reconnaissance_Intelligence.md` | Passive/active recon |
| **Phase 2: Surface** | `workflow/Phase2_Attack_Surface_Mapping.md` | Map endpoints, params, APIs |
| **Phase 3: Threat Model** | `workflow/Phase3_Threat_Modeling.md` | Identify threats, trust boundaries |
| **Phase 4: Advanced Patterns** | (in `phase4-advanced/`) | WebSocket, crypto, DoS, business logic |
| **Phase 5: Playbooks** | (in `playbook-*`) | Per-vuln-class testing |
| **Phase 6: Exploit** | `workflow/Phase6_Exploit_Validation_Impact.md` | Validate, measure impact |
| **Phase 7: Chain** | (in `exploit-kb-5/`) | Multi-step attacks |
| **Phase 8: Report** | `workflow/Phase8_Reporting_Remediation.md` | Final report + remediation |

---

## 🤖 Orchestrator

Adaptive workflow engine for coordination, decision-making, and state management.

| Library | Files | Purpose |
|---|---|---|
| `orchestrator-core/` | 8 | Workflow controller, report generator, finding correlator |
| `decision-engine/` | 9 | Execution planner, confidence scoring, adaptive planner |
| `memory-state/` | 9 | Knowledge cache, resume engine, context compression |
| `adaptive-reasoning/` | 9 | Feedback loop, adaptive router, priority optimizer |
| `reporting-quality/` | 9 | Assessment packager, remediation engine, quality gate |

---

## 📂 Full File Index by Category

### `adaptive-reasoning/` (9 files)

- `adaptive-reasoning/Adaptive_Router/Adaptive_Router.md` — Adaptive Router
- `adaptive-reasoning/Attack_Path_Builder/Attack_Path_Builder.md` — Attack Path Builder
- `adaptive-reasoning/Confidence_Updater/Confidence_Updater.md` — Confidence Updater
- `adaptive-reasoning/Correlation_Engine/Correlation_Engine.md` — Correlation Engine
- `adaptive-reasoning/Feedback_Loop/Feedback_Loop.md` — Feedback Loop
- `adaptive-reasoning/Hypothesis_Manager/Hypothesis_Manager.md` — Hypothesis Manager
- `adaptive-reasoning/Priority_Optimizer/Priority_Optimizer.md` — Priority Optimizer
- `adaptive-reasoning/README.md` — Pack D Part 4 — Adaptive Reasoning Engine
- `adaptive-reasoning/Reasoning_Engine/Reasoning_Engine.md` — Reasoning Engine

### `decision-engine/` (9 files)

- `decision-engine/Adaptive_Planner/Adaptive_Planner.md` — Adaptive Planner
- `decision-engine/Confidence_Scoring/Confidence_Scoring.md` — Confidence Scoring
- `decision-engine/Decision_Rules/Decision_Rules.md` — Decision Rules
- `decision-engine/Execution_Planner/Execution_Planner.md` — Execution Planner
- `decision-engine/README.md` — Pack D Part 2 — Decision Engine
- `decision-engine/Risk_Prioritizer/Risk_Prioritizer.md` — Risk Prioritizer
- `decision-engine/Strategy_Selector/Strategy_Selector.md` — Strategy Selector
- `decision-engine/Target_Classifier/Target_Classifier.md` — Target Classifier
- `decision-engine/Technology_Profiler/Technology_Profiler.md` — Technology Profiler

### `exploit-kb-1/` (5 files)

- `exploit-kb-1/Authentication/JWT_Token_Abuse.md` — JWT Token Abuse
- `exploit-kb-1/Authorization/IDOR_Knowledge.md` — IDOR Knowledge
- `exploit-kb-1/Injection/SQLi_Knowledge.md` — SQL Injection Knowledge
- `exploit-kb-1/Injection/SSRF_Knowledge.md` — SSRF Knowledge
- `exploit-kb-1/README.md` — Pack B Part 1 — Exploit Knowledge Base

### `exploit-kb-2/` (9 files)

- `exploit-kb-2/Browser_Security/CORS_Knowledge.md` — CORS
- `exploit-kb-2/Browser_Security/CSRF_Knowledge.md` — CSRF
- `exploit-kb-2/Client_Side/Clickjacking_Knowledge.md` — Clickjacking
- `exploit-kb-2/Client_Side/XSS_Knowledge.md` — Cross-Site Scripting (XSS)
- `exploit-kb-2/README.md` — Pack B Part 2 — Client & Server Exploitation
- `exploit-kb-2/Server_Side/Deserialization_Knowledge.md` — Insecure Deserialization
- `exploit-kb-2/Server_Side/Path_Traversal_Knowledge.md` — Path Traversal
- `exploit-kb-2/Server_Side/RCE_Knowledge.md` — Remote Code Execution
- `exploit-kb-2/Server_Side/XXE_Knowledge.md` — XML External Entity (XXE)

### `exploit-kb-3/` (10 files)

- `exploit-kb-3/API_Authorization/BFLA_Knowledge.md` — Broken Function Level Authorization (BFLA)
- `exploit-kb-3/API_Authorization/BOLA_Knowledge.md` — Broken Object Level Authorization (BOLA)
- `exploit-kb-3/API_Exposure/API_Rate_Limiting.md` — API Rate Limiting
- `exploit-kb-3/API_Exposure/Excessive_Data_Exposure.md` — Excessive Data Exposure
- `exploit-kb-3/API_Exposure/Mass_Assignment_Knowledge.md` — Mass Assignment
- `exploit-kb-3/API_Exposure/Shadow_API.md` — Shadow APIs
- `exploit-kb-3/GraphQL/GraphQL_Knowledge.md` — GraphQL
- `exploit-kb-3/README.md` — Pack B Part 3 — API & Modern Applications
- `exploit-kb-3/REST_API/REST_API_Knowledge.md` — REST API
- `exploit-kb-3/WebSocket/WebSocket_Knowledge.md` — WebSocket

### `exploit-kb-4/` (11 files)

- `exploit-kb-4/AWS/AWS_IAM_Knowledge.md` — AWS IAM
- `exploit-kb-4/AWS/S3_Knowledge.md` — Amazon S3
- `exploit-kb-4/Azure/Azure_Identity_Knowledge.md` — Azure Identity
- `exploit-kb-4/CI_CD/CI_CD_Knowledge.md` — CI/CD Security
- `exploit-kb-4/Containers/Docker_Knowledge.md` — Docker Security
- `exploit-kb-4/GCP/GCP_IAM_Knowledge.md` — Google Cloud IAM
- `exploit-kb-4/IAM/Identity_Access_Knowledge.md` — Identity & Access Management
- `exploit-kb-4/Kubernetes/Kubernetes_Knowledge.md` — Kubernetes Security
- `exploit-kb-4/README.md` — Pack B Part 4 — Cloud & Infrastructure Knowledge
- `exploit-kb-4/Secrets/Secrets_Management.md` — Secrets Management
- `exploit-kb-4/Web_Infrastructure/Nginx_Apache_Knowledge.md` — Web Infrastructure

### `exploit-kb-5/` (9 files)

- `exploit-kb-5/AI_Reasoning/Multi_Step_Attack_Planning.md` — Multi-Step Attack Planning
- `exploit-kb-5/AI_Reasoning/Root_Cause_Correlation.md` — Root Cause Correlation
- `exploit-kb-5/Business_Logic/Account_Recovery_Abuse.md` — Account Recovery Abuse
- `exploit-kb-5/Business_Logic/Payment_Workflow_Abuse.md` — Payment Workflow Abuse
- `exploit-kb-5/Case_Studies/High_Impact_Bug_Bounty_Patterns.md` — High-Impact Bug Bounty Patterns
- `exploit-kb-5/Exploit_Chains/IDOR_to_Privilege_Escalation.md` — IDOR → Privilege Escalation
- `exploit-kb-5/Exploit_Chains/SSRF_to_Cloud_Compromise.md` — SSRF → Cloud Compromise
- `exploit-kb-5/Impact_Escalation/Impact_Correlation.md` — Impact Correlation
- `exploit-kb-5/README.md` — Pack B Part 5 — Exploit Chains & AI Reasoning

### `memory-state/` (9 files)

- `memory-state/Assessment_State_Manager/Assessment_State_Manager.md` — Assessment State Manager
- `memory-state/Checkpoint_Manager/Checkpoint_Manager.md` — Checkpoint Manager
- `memory-state/Context_Compression/Context_Compression.md` — Context Compression
- `memory-state/Evidence_Store/Evidence_Store.md` — Evidence Store
- `memory-state/Finding_Repository/Finding_Repository.md` — Finding Repository
- `memory-state/Knowledge_Cache/Knowledge_Cache.md` — Knowledge Cache
- `memory-state/README.md` — Pack D Part 3 — Memory & State Management
- `memory-state/Resume_Engine/Resume_Engine.md` — Resume Engine
- `memory-state/Session_Memory/Session_Memory.md` — Session Memory

### `orchestrator-core/` (8 files)

- `orchestrator-core/Context_Manager/Context_Manager.md` — Context Manager
- `orchestrator-core/Core/Orchestrator.md` — Orchestrator Core
- `orchestrator-core/Finding_Correlator/Finding_Correlator.md` — Finding Correlator
- `orchestrator-core/Knowledge_Loader/Knowledge_Loader.md` — Knowledge Loader
- `orchestrator-core/README.md` — Pack D Part 1 — Orchestrator Core
- `orchestrator-core/Report_Generator/Report_Generator.md` — Report Generator
- `orchestrator-core/Router/Module_Router.md` — Module Router
- `orchestrator-core/Workflow_Controller/Workflow_Controller.md` — Workflow Controller

### `phase1-auth/` (5 files)

- `phase1-auth/01_Authentication/Broken_Authentication.md` — Broken Authentication
- `phase1-auth/01_Authentication/JWT_Weaknesses.md` — JWT Weaknesses
- `phase1-auth/02_Authorization/Broken_Access_Control.md` — Broken Access Control
- `phase1-auth/02_Authorization/IDOR.md` — Insecure Direct Object Reference (IDOR)
- `phase1-auth/README.md` — Pack A Part 1 — Authentication & Authorization

### `phase2-injection/` (6 files)

- `phase2-injection/03_Input_Validation/Input_Validation.md` — Input Validation
- `phase2-injection/03_Input_Validation/Mass_Assignment.md` — Mass Assignment
- `phase2-injection/04_Injection/Command_Injection.md` — Command Injection
- `phase2-injection/04_Injection/SQL_Injection.md` — SQL Injection
- `phase2-injection/04_Injection/Server_Side_Template_Injection.md` — Server-Side Template Injection
- `phase2-injection/README.md` — Pack A Part 2 — Input Validation & Injection

### `phase3-session-api/` (9 files)

- `phase3-session-api/05_Session_Management/Session_Expiration.md` — Session Expiration
- `phase3-session-api/05_Session_Management/Session_Fixation.md` — Session Fixation
- `phase3-session-api/06_File_Handling/File_Upload.md` — File Upload
- `phase3-session-api/06_File_Handling/Path_Traversal.md` — Path Traversal
- `phase3-session-api/07_API_Security/CORS_CSP.md` — CORS & CSP
- `phase3-session-api/07_API_Security/CSRF.md` — Cross-Site Request Forgery (CSRF)
- `phase3-session-api/07_API_Security/GraphQL_Security.md` — GraphQL Security
- `phase3-session-api/07_API_Security/REST_API_Security.md` — REST API Security
- `phase3-session-api/README.md` — Pack A Part 3 — Session Management, File Handling & API Security

### `phase4-advanced/` (13 files)

- `phase4-advanced/08_Client_Side/Clickjacking.md` — Clickjacking
- `phase4-advanced/08_Client_Side/DOM_XSS.md` — DOM-based XSS
- `phase4-advanced/09_Server_Side/Insecure_Deserialization.md` — Insecure Deserialization
- `phase4-advanced/09_Server_Side/SSRF.md` — Server-Side Request Forgery
- `phase4-advanced/09_Server_Side/XXE.md` — XML External Entity
- `phase4-advanced/10_Cryptography/Weak_Cryptography.md` — Weak Cryptography
- `phase4-advanced/11_Cloud_Infrastructure/Cloud_Misconfiguration.md` — Cloud Misconfiguration
- `phase4-advanced/12_WebSocket/WebSocket_Security.md` — WebSocket Security
- `phase4-advanced/13_Information_Disclosure/Information_Disclosure.md` — Information Disclosure
- `phase4-advanced/14_Denial_of_Service/Resource_Exhaustion.md` — Resource Exhaustion
- `phase4-advanced/15_Security_Misconfiguration/Debug_Exposure.md` — Debug Exposure
- `phase4-advanced/16_Business_Logic/Workflow_Bypass.md` — Workflow Bypass
- `phase4-advanced/README.md` — Pack A Part 4 — Advanced Attack Patterns

### `playbook-advanced/` (9 files)

- `playbook-advanced/AI_Orchestration/AI_Reasoning_Playbook.md` — AI Orchestration Playbook
- `playbook-advanced/Business_Logic/Business_Logic_Playbook.md` — Business Logic Playbook
- `playbook-advanced/Exploit_Chaining/Exploit_Chaining_Playbook.md` — Exploit Chaining Playbook
- `playbook-advanced/False_Positive_Review/Validation_Playbook.md` — Validation & False Positive Review
- `playbook-advanced/High_Impact_Hunting/High_Impact_Bug_Playbook.md` — High-Impact Bug Hunting Playbook
- `playbook-advanced/README.md` — Pack C Part 5 — Advanced Assessment Playbooks
- `playbook-advanced/Reporting_Remediation/Reporting_Playbook.md` — Reporting & Remediation Playbook
- `playbook-advanced/Security_Architecture/Architecture_Review_Playbook.md` — Security Architecture Review
- `playbook-advanced/Threat_Modeling/Threat_Modeling_Playbook.md` — Threat Modeling Playbook

### `playbook-cloud/` (10 files)

- `playbook-cloud/AWS/AWS_Assessment_Playbook.md` — AWS Assessment Playbook
- `playbook-cloud/Azure/Azure_Assessment_Playbook.md` — Azure Assessment Playbook
- `playbook-cloud/CI_CD/CI_CD_Playbook.md` — CI/CD Security Playbook
- `playbook-cloud/Docker/Docker_Playbook.md` — Docker Security Playbook
- `playbook-cloud/GCP/GCP_Assessment_Playbook.md` — GCP Assessment Playbook
- `playbook-cloud/IAM/IAM_Playbook.md` — IAM Playbook
- `playbook-cloud/Kubernetes/Kubernetes_Playbook.md` — Kubernetes Security Playbook
- `playbook-cloud/README.md` — Pack C Part 4 — Cloud & Infrastructure Playbooks
- `playbook-cloud/Reverse_Proxy/Reverse_Proxy_Playbook.md` — Reverse Proxy Playbook
- `playbook-cloud/Secrets/Secrets_Management_Playbook.md` — Secrets Management Playbook

### `playbook-core/` (6 files)

- `playbook-core/API/API_Audit_Playbook.md` — API Audit Playbook
- `playbook-core/Authentication/Login_Testing_Playbook.md` — Login Testing Playbook
- `playbook-core/Authorization/Access_Control_Playbook.md` — Access Control Playbook
- `playbook-core/Injection/Injection_Playbook.md` — Injection Playbook
- `playbook-core/README.md` — Pack C Part 1 — Core Playbooks
- `playbook-core/Recon_Playbooks/Recon_Playbook.md` — Recon Playbook

### `playbook-modern/` (9 files)

- `playbook-modern/API_Gateway/API_Gateway_Playbook.md` — API Gateway Playbook
- `playbook-modern/Event_Driven/Event_Driven_Playbook.md` — Event-Driven Systems Playbook
- `playbook-modern/GraphQL/GraphQL_Playbook.md` — GraphQL Playbook
- `playbook-modern/JWT/JWT_Playbook.md` — JWT Playbook
- `playbook-modern/Microservices/Microservices_Playbook.md` — Microservices Playbook
- `playbook-modern/OAuth_OIDC/OAuth_OIDC_Playbook.md` — OAuth 2.0 / OpenID Connect Playbook
- `playbook-modern/README.md` — Pack C Part 3 — Modern Application Playbooks
- `playbook-modern/SPA/SPA_Playbook.md` — Single Page Application Playbook
- `playbook-modern/WebSocket/WebSocket_Playbook.md` — WebSocket Playbook

### `playbook-vuln/` (9 files)

- `playbook-vuln/CSRF/CSRF_Playbook.md` — CSRF Playbook
- `playbook-vuln/Deserialization/Deserialization_Playbook.md` — Insecure Deserialization Playbook
- `playbook-vuln/File_Upload/File_Upload_Playbook.md` — File Upload Playbook
- `playbook-vuln/Path_Traversal/Path_Traversal_Playbook.md` — Path Traversal Playbook
- `playbook-vuln/RCE/RCE_Playbook.md` — Remote Code Execution Playbook
- `playbook-vuln/README.md` — Pack C Part 2 — Web Vulnerability Playbooks
- `playbook-vuln/SSRF/SSRF_Playbook.md` — SSRF Playbook
- `playbook-vuln/XSS/XSS_Playbook.md` — XSS Playbook
- `playbook-vuln/XXE/XXE_Playbook.md` — XXE Playbook

### `reporting-quality/` (9 files)

- `reporting-quality/Assessment_Packager/Assessment_Packager.md` — Assessment Packager
- `reporting-quality/Evidence_Validator/Evidence_Validator.md` — Evidence Validator
- `reporting-quality/Executive_Summary/Executive_Summary.md` — Executive Summary Generator
- `reporting-quality/Finding_Deduplicator/Finding_Deduplicator.md` — Finding Deduplicator
- `reporting-quality/Quality_Gate_Automation/Quality_Gate_Automation.md` — Quality Gate Automation
- `reporting-quality/README.md` — Pack D Part 5 — Reporting & Quality Automation
- `reporting-quality/Remediation_Engine/Remediation_Engine.md` — Remediation Recommendation Engine
- `reporting-quality/Report_Assembler/Report_Assembler.md` — Report Assembler
- `reporting-quality/Severity_Normalizer/Severity_Normalizer.md` — Severity Normalizer

### `workflow/` (8 files)

- `workflow/Phase1_Reconnaissance_Intelligence.md` — WebHunter OS v1.0
- `workflow/Phase2_Attack_Surface_Mapping.md` — WebHunter OS v1.0
- `workflow/Phase3_Threat_Modeling.md` — WebHunter OS v1.0
- `workflow/Phase4_Technical_Security_Analysis.md` — WebHunter OS v1.0
- `workflow/Phase5_Business_Logic_Analysis.md` — WebHunter OS v1.0
- `workflow/Phase6_Exploit_Validation_Impact.md` — WebHunter OS v1.0
- `workflow/Phase7_Quality_Gate.md` — WebHunter OS v1.0
- `workflow/Phase8_Reporting_Remediation.md` — WebHunter OS v1.0

---

## 💡 Usage Tips

- **Start with INDEX.md** for any new web audit task
- **Phase-based queries** → check the Audit Phases section
- **Vulnerability hunts** → check Vulnerability Classes section
- **Tech stack audits** → check Tech Stacks section
- **Cloud audits** → check Cloud & Infrastructure section
- **End with quality gate** (`reporting-quality/`) before delivery

## 🔄 Integration with Other Skills

- `bughunter-os` — for smart contract audits (combine for hybrid DeFi+web targets)
- `soul.md` (bozagentic) — operating philosophy + tool execution

## 🔄 Update Policy

This index is auto-generated. To regenerate after adding new files, re-run the indexer script.
