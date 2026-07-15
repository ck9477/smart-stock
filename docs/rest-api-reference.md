# REST API Reference

**Base URL:** `http://localhost:5000`

All responses are JSON. Error responses: `{"error": "<message>"}`.

---

## General

### Health Check

| Method | Path | Response |
|---|---|---|
| GET | `/test` | `{"message": "working"}` |

---

## Users — `/users`

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/users` | `{"name", "email", "password"}` | `{"id": int}` |
| GET | `/users` | — | `[{"id", "name", "email"}]` |
| GET | `/users/<id>` | — | `{"id", "name", "email"}` |
| PUT | `/users/<id>` | `{"name"?, "email"?}` | `{"message": "updated"}` |
| DELETE | `/users/<id>` | — | `{"message": "deleted"}` |
| POST | `/users/login` | `{"email", "password"}` | `{"message", "user_id"}` |
| GET | `/users/by-email/<email>` | — | `{"id", "name", "email"}` |
| GET | `/users/search?name=` | query: `name` | `[{"id", "name", "email"}]` |
| GET | `/users/count` | — | `{"count": int}` |

**Notes:**
- Login validates password hash via `werkzeug.security` and returns the `user_id`. No JWT or session is created — the client is responsible for storing the user ID (frontend uses localStorage).
- Password is never returned in responses.
- `search` performs a partial match on name.

---

## Products — `/products`

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/products` | `{"name", "category_id", "volume_ml"?, "code"?}` | `{"id", "name", "category_id", "volume_ml", "code"}` |
| GET | `/products` | — | `[{"id", "name", "category_id", "volume_ml", "code"}]` |
| GET | `/products/<id>` | — | `{"id", "name", "category_id", "volume_ml", "code"}` |
| PUT | `/products/<id>` | `{"name"?, "category_id"?, "volume_ml"?}` | `{"id", "name", "category_id", "volume_ml"}` |
| DELETE | `/products/<id>` | — | `{"message": "deleted"}` |

**Notes:**
- `code` is the product barcode. It is unique but nullable.
- `volume_ml` is nullable — use it for package sizes.

---

## Category — `/category`

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/category` | `{"name", "range_id"}` | `{"id": int}` |
| GET | `/category` | — | `[{"id", "name", "range_id"}]` |
| GET | `/category/<id>` | — | `{"id", "name", "range_id"}` |

---

## Range — `/range`

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/range` | `{"range_name", "Number_of_days"}` | `{"id": int}` |
| GET | `/range` | — | `[{"id", "range_name", "Number_of_days"}]` |
| GET | `/range/<id>` | — | `{"id", "range_name", "Number_of_days"}` |
| PUT | `/range/<id>` | `{"range_name"?, "Number_of_days"?}` | `{"message": "updated"}` |
| DELETE | `/range/<id>` | — | `{"message": "deleted"}` |

**Notes:**
- `range_name` should describe the cycle (e.g., "יומי", "שבועי").
- `Number_of_days` is the cycle length in days.

---

## Receipts — `/receipts`

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/receipts` | `{"user_id"}` | `{"id": int}` |
| POST | `/receipts/upload` | **multipart:** `receipt` (file), `user_id` | `{"receipt_id", "products": [...]}` |
| PATCH | `/receipts/<id>` | `{"user_id"}` | `{"id", "user_id", "receipt_date"}` |
| PATCH | `/receipts/<id>/products/<item_id>` | `{"product_id"?, "amount"?}` | `{"id", "receipt_id", "product_id", "amount"}` |
| POST | `/receipts/process/<id>` | `{"products": [...]}` | `{"receipt_id", "products": [...]}` |
| GET | `/receipts/user/<user_id>` | — | `[{"id", "user_id"}]` |
| GET | `/receipts/<id>/products` | — | `[{"id", "receipt_id", "product_id", "product_code", "product_name", "volume_ml", "amount"}]` |
| DELETE | `/receipts/<id>` | — | `{"message": "deleted"}` |

### Upload Details

`POST /receipts/upload` accepts multipart form data with:
- `receipt` — file (PDF, JSON, or text)
- `user_id` — integer

**Supported file formats:**

| Format | Parser | Method |
|---|---|---|
| **PDF** | pdfplumber | Text extraction from all pages |
| **JSON** | `json.loads` | `[{"code"/"product_code", "name", "quantity"/"amount"}]` or `{"products": [...]}` |
| **Text** | regex | Matches 6–14 digit barcodes + Hebrew/English text |

The upload response:
```json
{
  "receipt_id": 1,
  "products": [
    {
      "reception_id": 1,
      "product_id": 5,
      "product_code": "7290000288062",
      "name": "עגבניות",
      "amount": 3
    }
  ]
}
```

---

## Reception Products — `/reception-products`

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/reception-products` | `{"receipts_id", "products_id", "amount"}` | `{"id": int}` |
| GET | `/reception-products` | — | `[{"id", "receipts_id", "products_id", "amount"}]` |
| GET | `/reception-products/<id>` | — | `{"id", "receipts_id", "products_id", "amount"}` |
| DELETE | `/reception-products/<id>` | — | `{"message": "deleted"}` |

---

## Shopping List — `/shopping`

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/shopping` | `{"user_id", "product_id", "amount"? (1), "range_enum"?}` | `{"id": int}` |
| GET | `/shopping/user/<user_id>` | — | `[{"id", "product_id", "amount", "range_enum"}]` |
| GET | `/shopping/<id>` | — | `{"id", "product_id", "amount", "range_enum"}` |
| PUT | `/shopping/<id>` | `{"product_id"?, "amount"?, "range_enum"?}` | `{"message": "updated"}` |
| DELETE | `/shopping/<id>` | — | `{"message": "deleted"}` |
| POST | `/shopping/generate/<user_id>` | — | `{"message", "user_id", "products_added": [...], "total_added"}` |

### Generate Logic

`POST /shopping/generate/<user_id>` reads `product_range_for_the_user` for the given user, and for each product-range mapping not yet present in the shopping list, creates a `Shopping_list` entry with `amount=1` and `range_enum` from the product-range mapping.

Response:
```json
{
  "message": "Shopping list generated based on product ranges",
  "user_id": 1,
  "products_added": [
    {"product_id": 1, "product_name": "חלב תנובה 3%"},
    {"product_id": 3, "product_name": "לחם אחיד"}
  ],
  "total_added": 2
}
```

---

## Product Range for User — `/product-range-for-user`

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/product-range-for-user` | `{"user_id", "Products_id", "Range_id"}` | `{"id": int}` |
| GET | `/product-range-for-user` | — | `[{"id", "user_id", "Products_id", "Range_id"}]` |
| GET | `/product-range-for-user/<id>` | — | `{"id", "user_id", "Products_id", "Range_id"}` |
| PUT | `/product-range-for-user/<id>` | `{"user_id"?, "Products_id"?, "Range_id"?}` | `{"message": "updated"}` |
| DELETE | `/product-range-for-user/<id>` | — | `{"message": "deleted"}` |

---

## API Conventions

### Create Responses
`POST` endpoints that create resources return `{"id": <new_id>}`. The client typically merges the request data + returned ID into its local state.

### Update Responses
`PUT`/`PATCH` endpoints return `{"message": "updated"}` or the updated object. The client should use the request payload + ID to update its local state.

### Delete Responses
`DELETE` endpoints return `{"message": "deleted"}`. The client should remove the item from local state by ID.

### Error Responses
All errors follow the format `{"error": "<description>"}`. HTTP status codes are used appropriately (400 for bad requests, 404 for not found, 500 for server errors).
