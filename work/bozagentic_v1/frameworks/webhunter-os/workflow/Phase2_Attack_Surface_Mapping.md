# WebHunter OS v1.0

# Phase 2 --- Attack Surface Mapping

Version: 1.0

------------------------------------------------------------------------

# Objective

Transform reconnaissance data into a structured map of every reachable
attack surface.

The objective is to identify all locations where an attacker can
interact with, influence, or abuse the application.

------------------------------------------------------------------------

# Scope

Applicable to:

-   Web Applications
-   REST APIs
-   GraphQL APIs
-   SPAs
-   Admin Portals
-   Mobile Backends

------------------------------------------------------------------------

# Philosophy

You cannot secure what you have not mapped.

Attack surface mapping is the bridge between reconnaissance and
vulnerability analysis.

------------------------------------------------------------------------

# AI Mindset

Focus on exposure, not exploitation.

Ask:

-   Where does user input enter?
-   Which endpoints change application state?
-   Which interfaces require trust?
-   Which components are externally accessible?
-   Which features appear security-sensitive?

------------------------------------------------------------------------

# Workflow

1.  Input Entry Points
2.  Endpoint Classification
3.  Authentication Boundaries
4.  Authorization Boundaries
5.  File Handling Surface
6.  Business Workflow Mapping
7.  Client-side Surface
8.  External Integrations
9.  High-value Targets
10. Attack Surface Matrix

------------------------------------------------------------------------

# Mapping Modules

## Module 1 --- Input Entry Points

Identify:

-   Forms
-   Query Parameters
-   Path Parameters
-   Headers
-   Cookies
-   JSON Bodies
-   Multipart Uploads
-   WebSockets

Output:

-   Input Inventory

------------------------------------------------------------------------

## Module 2 --- Endpoint Classification

Classify endpoints as:

-   Public
-   Authenticated
-   Admin
-   Internal
-   Deprecated

Output:

-   Endpoint Classification Matrix

------------------------------------------------------------------------

## Module 3 --- Authentication Boundaries

Analyze:

-   Login Required
-   Anonymous Access
-   Session Creation
-   Token Issuance
-   MFA Enforcement

Output:

-   Authentication Boundary Map

------------------------------------------------------------------------

## Module 4 --- Authorization Boundaries

Identify:

-   User Roles
-   Privileged Actions
-   Ownership Checks
-   Access Restrictions

Output:

-   Authorization Matrix

------------------------------------------------------------------------

## Module 5 --- File Handling Surface

Map:

-   Uploads
-   Downloads
-   Imports
-   Exports
-   Image Processing

Output:

-   File Handling Inventory

------------------------------------------------------------------------

## Module 6 --- Business Workflow Mapping

Document workflows such as:

-   Registration
-   Login
-   Payments
-   Orders
-   Profile Management
-   Password Reset

Output:

-   Business Workflow Diagram

------------------------------------------------------------------------

## Module 7 --- Client-side Surface

Analyze:

-   JavaScript APIs
-   Local Storage
-   Session Storage
-   Service Workers
-   Browser Features

Output:

-   Client-side Surface Report

------------------------------------------------------------------------

## Module 8 --- External Integrations

Identify interactions with:

-   Payment Providers
-   Identity Providers
-   Cloud Services
-   Messaging Services
-   Analytics

Output:

-   Integration Map

------------------------------------------------------------------------

## Module 9 --- High-value Targets

Prioritize:

-   Admin Panels
-   Payment Functions
-   Account Management
-   File Uploads
-   API Gateways
-   Sensitive Data Endpoints

Output:

-   High-value Target List

------------------------------------------------------------------------

## Module 10 --- Attack Surface Matrix

Create a consolidated matrix including:

-   Component
-   Exposure
-   Trust Level
-   Authentication
-   Business Impact
-   Priority

Output:

-   Attack Surface Matrix

------------------------------------------------------------------------

# Deliverables

-   Input Inventory
-   Endpoint Classification
-   Authentication Boundary Map
-   Authorization Matrix
-   File Handling Inventory
-   Business Workflow Map
-   Client-side Surface Report
-   Integration Map
-   High-value Targets
-   Attack Surface Matrix

------------------------------------------------------------------------

# Exit Criteria

Proceed only if:

-   Entry points mapped
-   Endpoints classified
-   Trust boundaries identified
-   Business workflows documented
-   High-value targets prioritized

------------------------------------------------------------------------

# Common Mistakes

-   Ignoring authenticated-only features
-   Overlooking admin interfaces
-   Missing hidden upload functionality
-   Treating all endpoints equally
-   Skipping workflow analysis

------------------------------------------------------------------------

# AI Reasoning Checklist

Before Phase 3:

-   Are all input vectors identified?
-   Are trust boundaries understood?
-   Are critical workflows mapped?
-   Are high-impact components prioritized?

If any answer is "No", continue mapping.

------------------------------------------------------------------------

# Transition

Proceed to **Phase 3 --- Threat Modeling**
