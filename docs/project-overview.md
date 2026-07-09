# Project Overview

## What is Smart Stock?

Smart Stock is a smart household inventory and shopping list management system.

The system automates the shopping workflow:

- Receipt processing
- Product tracking
- Consumption analysis
- Smart shopping list generation

The backend provides the business logic, data management, and REST API consumed by the frontend application.

---

## Core Goals

1. Automate shopping list creation based on consumption patterns
2. Track household purchases through receipt processing
3. Analyze purchase cycles and product usage
4. Predict product depletion
5. Support future automation capabilities

---

## System Capabilities

### Receipt Processing

- Upload receipts as PDF, JSON, or text
- Extract products from receipts
- Match products by barcode or name
- Store purchase history

### Shopping List Generation

- Define purchase ranges per product
- Generate shopping lists automatically
- Manage shopping list items

### Purchase Statistics

The system calculates:

- Purchase cycles
- Stability scores
- Purchase trends
- Days since last purchase
- Urgency scores

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| ORM | SQLAlchemy |
| Database | Microsoft SQL Server 2022 |
| Receipt Parsing | pdfplumber, regex, JSON |
| Browser Automation | Playwright |
| Deployment | Docker |

---

## Related Documentation

- [System Architecture](system-architecture.md)
- [Database Schema](database-schema.md)
- [REST API Reference](rest-api-reference.md)
- [Development Guide](development-guide.md)
- [Future Roadmap](future-roadmap.md)