# Database Schema

## ER Diagram

```
┌──────────┐       ┌──────────────┐       ┌─────────────────────┐
│   users  │       │   receipts   │       │ reception_products  │
├──────────┤       ├──────────────┤       ├─────────────────────┤
│ id    PK │──┐    │ id        PK │──┐    │ id               PK │
│ name     │  └───▶│ user_id  FK │  └───▶│ receipts_id     FK │
│ email UQ │       │ receipt_date│        │ products_id     FK │──┐
│ pw_hash  │       └──────────────┘       │ amount             │  │
│ created  │                              └─────────────────────┘  │
└──────────┘                                                        │
      │                                                             │
      │    ┌─────────────────────────┐                              │
      ├───▶│product_range_for_the_user│                             │
      │    ├─────────────────────────┤     ┌──────────────┐         │
      │    │ id                   PK │     │   products   │◀────────┘
      │    │ user_id              FK │     ├──────────────┤
      │    │ Products_id          FK │──┐  │ id        PK │
      │    │ Range_id             FK │  └─▶│ name         │
      │    └─────────────────────────┘     │ category_id FK│──┐
      │                                    │ code UQ      │  │
      │    ┌─────────────────┐             │ volume_ml    │  │
      ├───▶│ Shopping_list   │             └──────────────┘  │
      │    ├─────────────────┤                               │
      │    │ id           PK │      ┌──────────────┐         │
      │    │ Products_id  FK │──┐   │   category   │◀────────┘
      │    │ amount          │  │   ├──────────────┤
      │    │ Range_enum   FK │  │   │ id        PK │
      │    │ user_id      FK │  │   │ name         │
      │    └─────────────────┘  │   │ Range_id  FK │──┐
      │                         │   └──────────────┘  │
      │                         │                      │
      │    ┌──────────┐         │   ┌──────────┐       │
      └───▶│  Range   │◀────────┘   │  Range   │◀──────┘
           ├──────────┤             ├──────────┤
           │ id    PK │             │ (same)    │
           │range_name│             └──────────┘
           │Num._days │
           └──────────┘
```

**Key Relationships:**

- A **User** has many **Receipts**, **ShoppingList** items, and **ProductRangeForTheUser** mappings
- A **Receipt** contains many **ReceptionProducts** (line items), each linking to a **Product**
- A **Product** belongs to one **Category**
- **Range** defines cycle frequency (daily, weekly, etc.) — referenced by Category, ShoppingList, and ProductRangeForTheUser
- **ShoppingList** links a User + Product + optional Range with an amount
- **ProductRangeForTheUser** defines "this user buys product X every Y days" — powers shopping list generation

---

## Tables

### `Range`

Defines consumption/purchase cycle frequencies.

| Column | Type | Constraints |
|---|---|---|
| `id` | INT | PK, IDENTITY |
| `range_name` | NVARCHAR(25) | NOT NULL |
| `Number_of_days` | INT | NOT NULL |

**Seed data:**

| range_name | Number_of_days |
|---|---|
| יומי (Daily) | 1 |
| שבועי (Weekly) | 7 |
| דו שבועי (Bi-weekly) | 14 |
| חודשי (Monthly) | 30 |
| רבעוני (Quarterly) | 90 |

---

### `users`

Registered users of the system.

| Column | Type | Constraints |
|---|---|---|
| `id` | INT | PK, IDENTITY |
| `name` | NVARCHAR(25) | NOT NULL |
| `email` | NVARCHAR(30) | NOT NULL, UNIQUE |
| `password_hash` | NVARCHAR(255) | NOT NULL |
| `created_at` | DATETIME2 | DEFAULT SYSUTCDATETIME() |

Password hashing: `werkzeug.security` (scrypt).

---

### `category`

Product categories, each associated with a default purchase range.

| Column | Type | Constraints |
|---|---|---|
| `id` | INT | PK, IDENTITY |
| `name` | NVARCHAR(50) | NOT NULL |
| `Range_id` | INT | FK → Range(id) ON DELETE CASCADE, NOT NULL |

**Seed data:** מוצרי חלב, לחם ומאפים, ירקות ופירות, בשר ועוף, מוצרים יבשים, מוצרי ניקוי, משקאות.

---

### `products`

Individual products tracked by the system.

| Column | Type | Constraints |
|---|---|---|
| `id` | INT | PK, IDENTITY |
| `name` | NVARCHAR(50) | NOT NULL |
| `category_id` | INT | FK → category(id) ON DELETE CASCADE, NOT NULL |
| `code` | NVARCHAR(50) | UNIQUE, NULL |
| `volume_ml` | INT | NULL |

`code` stores the product barcode. `volume_ml` stores package size when relevant.

---

### `receipts`

A receipt uploaded by a user.

| Column | Type | Constraints |
|---|---|---|
| `id` | INT | PK, IDENTITY |
| `user_id` | INT | FK → users(id) ON DELETE CASCADE, NOT NULL |
| `receipt_date` | DATETIME2 | NOT NULL, DEFAULT SYSUTCDATETIME() |

---

### `reception_products`

Line items in a receipt — one product per row.

| Column | Type | Constraints |
|---|---|---|
| `id` | INT | PK, IDENTITY |
| `receipts_id` | INT | FK → receipts(id) ON DELETE CASCADE, NOT NULL |
| `products_id` | INT | FK → products(id) ON DELETE CASCADE, NOT NULL |
| `amount` | INT | NOT NULL |

---

### `Shopping_list`

The user's current shopping list — which products to buy and how many.

| Column | Type | Constraints |
|---|---|---|
| `id` | INT | PK, IDENTITY |
| `Products_id` | INT | FK → products(id) ON DELETE CASCADE, NOT NULL |
| `amount` | INT | NOT NULL |
| `Range_enum` | INT | FK → Range(id), NULL |
| `user_id` | INT | FK → users(id) ON DELETE CASCADE, NOT NULL |

`Range_enum` references the cycle the item was generated for. NULL when manually added.

---

### `product_range_for_the_user`

Defines per-user purchase cycles: "this user buys product X every Y days."

| Column | Type | Constraints |
|---|---|---|
| `id` | INT | PK, IDENTITY |
| `user_id` | INT | FK → users(id) ON DELETE CASCADE, NOT NULL |
| `Products_id` | INT | FK → products(id), NOT NULL |
| `Range_id` | INT | FK → Range(id) ON DELETE CASCADE, NOT NULL |

This table drives the shopping list generation — when you call `POST /shopping/generate/<user_id>`, the system reads these mappings and creates `Shopping_list` entries for products due for repurchase.

---

## Demo Data Summary

The `docker/init.sql` script seeds the database with:

- **5 ranges** (daily → quarterly)
- **3 users** (demo accounts)
- **7 categories** (dairy, bread, vegetables, meat, dry goods, cleaning, beverages)
- **14 products** (milk, cheese, bread, challah, tomatoes, cucumbers, bananas, chicken breast, rice, pasta, cereal, cola, dish soap, shampoo)
- **4 sample receipts** with line items
- **5 product-range-user mappings**
- **4 shopping list entries**
