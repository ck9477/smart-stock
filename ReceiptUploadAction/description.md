# תיאור פעולה: העלאת קובץ קבלה ועריכה

## מה נוסף
- תמיכה בהעלאת קובץ קבלה דרך `POST /receipts/upload`
- שמירת פרטי הקבלה לטבלת `receipts`
- יצירת רשומות `reception_products` עבור מוצרים בקבלה
- אפשרות עריכה של קבלה (`PATCH /receipts/<receipt_id>`)
- אפשרות עריכה של מוצר בקבלה (`PATCH /receipts/<receipt_id>/products/<item_id>`)

## נתיב ההעלאה
`POST /receipts/upload`

גוף הבקשה:
- `receipt` — קובץ הקבלה
- `user_id` — מזהה המשתמש

## נתיב עדכון קבלה
`PATCH /receipts/<receipt_id>`

גוף JSON:
- `user_id` — מזהה משתמש חדש

## נתיב עדכון מוצר בקבלה
`PATCH /receipts/<receipt_id>/products/<item_id>`

גוף JSON:
- `product_id` — מזהה מוצר חדש
- `amount` — כמות חדשה
