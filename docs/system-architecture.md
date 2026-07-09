# System Architecture

## Architecture Style

Client-Server architecture with layered backend:
Frontend (React SPA)
|
| HTTP REST API (JSON)
|
v
Flask REST API
|
v
Service Layer
(business logic)
|
v
Repository Layer
(SQLAlchemy ORM)
|
v
SQL Server 2022

---

## Backend Architecture

### Layers

| Layer | Location | Responsibility |
|---|---|---|
| Controllers | Controller/ | HTTP handling, validation, responses |
| Services | Service/ | Business logic and processing |
| Repository | Repository/ | Database access |
| Models | models/ | SQLAlchemy entities |
| DTO | DTO/ | Request and response structures |

---

## Key Design Decisions

- Blueprint-based route organization
- SQLAlchemy ORM for database access
- Global CORS configuration
- Base controller for shared database session handling
- Current authentication flow uses user_id returned to client

---

## Main Services

## Receipt Processing

Flow:
File Upload
|
Receipt Parser
|
Product Extraction
|
Product Matching
|
Database Insert

---

## Shopping List Generation

Flow:

User Request
|
Shopping Service
|
Product Range Analysis
|
Shopping List Creation

---

## Statistics Engine

Calculates:

- Purchase cycles
- Stability
- Trends
- Urgency scores

---


---

# Deployment

Docker services:

Backend Container
|
|
Database Container
|
|
Database Initialization Container

Volumes:

- sql_data
- sql_log
- debug_screenshots

db-init
|
+-- creates schema
+-- inserts seed data
