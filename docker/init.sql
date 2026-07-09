-- ============================================================
-- SmartStock — Database Initialization Script
-- Aligned with authoritative schema (07/2026)
-- ============================================================

-- Create the database if it doesn't exist
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'SmartStock')
BEGIN
    CREATE DATABASE SmartStock;
END
GO

USE SmartStock;
GO

-- ============================================================
-- Tables (in dependency order)
-- ============================================================

-- Range
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Range')
BEGIN
    CREATE TABLE [Range] (
        id INT IDENTITY(1,1) PRIMARY KEY,
        range_name NVARCHAR(25) NOT NULL,
        Number_of_days INT NOT NULL
    );
END
GO

-- Users (schema dbo)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'users')
BEGIN
    CREATE TABLE users (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(25) NOT NULL,
        email NVARCHAR(30) NOT NULL UNIQUE,
        password_hash NVARCHAR(255) NOT NULL,
        created_at DATETIME2 NULL DEFAULT SYSDATETIME()
    );
END
GO

-- Category
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'category')
BEGIN
    CREATE TABLE category (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(50) NOT NULL,
        Range_id INT NOT NULL,
        CONSTRAINT FK_category_Range FOREIGN KEY (Range_id) REFERENCES [Range](id) ON DELETE CASCADE
    );
END
GO

-- Permissions (RBAC)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'permissions')
BEGIN
    CREATE TABLE permissions (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(80) NOT NULL UNIQUE,
        description NVARCHAR(200) NULL
    );
END
GO

-- Roles (RBAC)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'roles')
BEGIN
    CREATE TABLE roles (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(50) NOT NULL UNIQUE,
        description NVARCHAR(200) NULL
    );
END
GO

-- Products (with source tracking and OpenFoodFacts metadata)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'products')
BEGIN
    CREATE TABLE products (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(50) NOT NULL,
        category_id INT NOT NULL,
        volume_ml INT NULL,
        code NVARCHAR(50) NULL UNIQUE,
        source NVARCHAR(20) NULL DEFAULT 'manual',
        off_category NVARCHAR(100) NULL,
        off_brand NVARCHAR(100) NULL,
        CONSTRAINT FK_products_category FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE CASCADE,
        CONSTRAINT CK_products_source CHECK (source IN ('manual', 'openfoodfacts'))
    );
END
GO

-- Role-Permission (many-to-many)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'role_permission')
BEGIN
    CREATE TABLE role_permission (
        role_id INT NOT NULL,
        permission_id INT NOT NULL,
        PRIMARY KEY (role_id, permission_id),
        FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
        FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
    );
END
GO

-- User-Role (many-to-many)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'user_role')
BEGIN
    CREATE TABLE user_role (
        user_id INT NOT NULL,
        role_id INT NOT NULL,
        PRIMARY KEY (user_id, role_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
    );
END
GO

-- Receipts
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'receipts')
BEGIN
    CREATE TABLE receipts (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL,
        receipt_date DATETIME2 NULL DEFAULT SYSDATETIME(),
        CONSTRAINT FK_receipts_users FOREIGN KEY (user_id) REFERENCES users(id)
    );
END
GO

-- Reception_products
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'reception_products')
BEGIN
    CREATE TABLE reception_products (
        id INT IDENTITY(1,1) PRIMARY KEY,
        receipts_id INT NOT NULL,
        products_id INT NOT NULL,
        amount INT NOT NULL,
        CONSTRAINT FK_rp_receipts FOREIGN KEY (receipts_id) REFERENCES receipts(id),
        CONSTRAINT FK_rp_products FOREIGN KEY (products_id) REFERENCES products(id) ON DELETE CASCADE
    );
END
GO

-- Shopping_list
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Shopping_list')
BEGIN
    CREATE TABLE Shopping_list (
        id INT IDENTITY(1,1) PRIMARY KEY,
        Products_id INT NOT NULL,
        amount INT NOT NULL,
        Range_enum INT NOT NULL,
        user_id INT NOT NULL,
        CONSTRAINT FK_sl_products FOREIGN KEY (Products_id) REFERENCES products(id) ON DELETE CASCADE,
        CONSTRAINT FK_sl_range FOREIGN KEY (Range_enum) REFERENCES [Range](id),
        CONSTRAINT FK_sl_users FOREIGN KEY (user_id) REFERENCES users(id)
    );
END
GO

-- Product_range_for_the_user
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'product_range_for_the_user')
BEGIN
    CREATE TABLE product_range_for_the_user (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL,
        Products_id INT NOT NULL,
        Range_id INT NOT NULL,
        CONSTRAINT FK_prfu_users FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        CONSTRAINT FK_prfu_products FOREIGN KEY (Products_id) REFERENCES products(id),
        CONSTRAINT FK_prfu_range FOREIGN KEY (Range_id) REFERENCES [Range](id) ON DELETE CASCADE
    );
END
GO

-- User_Product_Learning (ML consumption patterns)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'User_Product_Learning')
BEGIN
    CREATE TABLE User_Product_Learning (
        user_id INT NOT NULL,
        product_id BIGINT NOT NULL,
        learned_gap FLOAT NULL,
        confidence FLOAT NULL,
        samples_count INT NULL,
        last_updated DATE NULL,
        product_id_new BIGINT NULL,
        product_id_fixed BIGINT NULL,
        CONSTRAINT PK_User_Product_Learning PRIMARY KEY (user_id, product_id)
    );
END
GO

-- ============================================================
-- Functions
-- ============================================================

-- fn_ProductUserStats — aggregated statistics per user/product/range
IF NOT EXISTS (SELECT * FROM sys.objects WHERE type = 'IF' AND name = 'fn_ProductUserStats')
BEGIN
    EXEC('
    CREATE FUNCTION dbo.fn_ProductUserStats()
    RETURNS TABLE
    AS
    RETURN
    (
        SELECT
            user_id,
            Products_id,
            Range_id,
            COUNT(*) OVER (PARTITION BY user_id) AS user_total,
            COUNT(*) OVER (PARTITION BY Products_id) AS product_total,
            COUNT(*) OVER (PARTITION BY Range_id) AS range_total
        FROM dbo.product_range_for_the_user
    );
    ')
END
GO

-- ============================================================
-- Demo Data
-- ============================================================

-- Ranges
IF NOT EXISTS (SELECT 1 FROM [Range])
BEGIN
    INSERT INTO [Range] (range_name, Number_of_days) VALUES
        (N'יומי', 1),
        (N'שבועי', 7),
        (N'דו שבועי', 14),
        (N'חודשי', 30),
        (N'רבעוני', 90);
END
GO

-- Demo Users
IF NOT EXISTS (SELECT 1 FROM users)
BEGIN
    INSERT INTO users (name, email, password_hash) VALUES
        (N'ישראל ישראלי', 'israel@example.com', 'scrypt:32768:8:1$hashed_demo_1'),
        (N'שרה כהן', 'sara@example.com', 'scrypt:32768:8:1$hashed_demo_2'),
        (N'דוד לוי', 'david@example.com', 'scrypt:32768:8:1$hashed_demo_3');
END
GO

-- Categories
IF NOT EXISTS (SELECT 1 FROM category)
BEGIN
    INSERT INTO category (name, Range_id) VALUES
        (N'מוצרי חלב', 1),
        (N'לחם ומאפים', 1),
        (N'ירקות ופירות', 1),
        (N'בשר ועוף', 2),
        (N'מוצרים יבשים', 3),
        (N'מוצרי ניקוי', 4),
        (N'משקאות', 2),
        (N'כללי', 3);
END
GO

-- Demo Permissions
IF NOT EXISTS (SELECT 1 FROM permissions)
BEGIN
    INSERT INTO permissions (name, description) VALUES
        (N'manage_users', N'ניהול משתמשים — יצירה, עריכה, מחיקה'),
        (N'manage_products', N'ניהול מוצרים — הוספה, עריכה, מחיקה'),
        (N'view_stats', N'צפייה בסטטיסטיקות ודוחות'),
        (N'manage_roles', N'ניהול תפקידים והרשאות'),
        (N'upload_receipts', N'העלאת קבלות וסריקת מוצרים');
END
GO

-- Demo Roles
IF NOT EXISTS (SELECT 1 FROM roles)
BEGIN
    INSERT INTO roles (name, description) VALUES
        (N'admin', N'מנהל מערכת — גישה מלאה'),
        (N'manager', N'מנהל — ניהול מוצרים וצפייה בסטטיסטיקות'),
        (N'user', N'משתמש רגיל — העלאת קבלות וצפייה ברשימות קניות');
END
GO

-- Role-Permission assignments
IF NOT EXISTS (SELECT 1 FROM role_permission)
BEGIN
    -- Admin gets all permissions
    INSERT INTO role_permission (role_id, permission_id)
    SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'admin';

    -- Manager: manage_products, view_stats, upload_receipts
    INSERT INTO role_permission (role_id, permission_id)
    SELECT r.id, p.id FROM roles r, permissions p
    WHERE r.name = 'manager' AND p.name IN ('manage_products', 'view_stats', 'upload_receipts');

    -- User: upload_receipts, view_stats
    INSERT INTO role_permission (role_id, permission_id)
    SELECT r.id, p.id FROM roles r, permissions p
    WHERE r.name = 'user' AND p.name IN ('upload_receipts', 'view_stats');
END
GO

-- User-Role assignments
IF NOT EXISTS (SELECT 1 FROM user_role)
BEGIN
    -- ישראל ישראלי = admin
    INSERT INTO user_role (user_id, role_id)
    SELECT u.id, r.id FROM users u, roles r WHERE u.email = 'israel@example.com' AND r.name = 'admin';

    -- שרה כהן = manager
    INSERT INTO user_role (user_id, role_id)
    SELECT u.id, r.id FROM users u, roles r WHERE u.email = 'sara@example.com' AND r.name = 'manager';

    -- דוד לוי = user
    INSERT INTO user_role (user_id, role_id)
    SELECT u.id, r.id FROM users u, roles r WHERE u.email = 'david@example.com' AND r.name = 'user';
END
GO

-- Products
IF NOT EXISTS (SELECT 1 FROM products)
BEGIN
    INSERT INTO products (name, category_id, code, volume_ml, source) VALUES
        (N'חלב תנובה 3%', 1, '7290000288024', 1000, 'manual'),
        (N'גבינה לבנה 5%', 1, '7290000288031', 250, 'manual'),
        (N'לחם אחיד', 2, '7290000288048', NULL, 'manual'),
        (N'חלה', 2, '7290000288055', NULL, 'manual'),
        (N'עגבניות', 3, '7290000288062', NULL, 'manual'),
        (N'מלפפון', 3, '7290000288079', NULL, 'manual'),
        (N'בננה', 3, '7290000288086', NULL, 'manual'),
        (N'חזה עוף טרי', 4, '7290000288093', NULL, 'manual'),
        (N'אורז בסמטי', 5, '7290000288109', 1000, 'manual'),
        (N'פסטה', 5, '7290000288116', 500, 'manual'),
        (N'דגני בוקר קוקומן', 5, '7290112495037', NULL, 'manual'),
        (N'קוקה קולה זירו', 7, '7290000288130', 1500, 'manual'),
        (N'סבון כלים', 6, '7290000288147', 750, 'manual'),
        (N'שמפו', 6, '7290000288154', 400, 'manual');
END
GO

-- Sample Receipts
IF NOT EXISTS (SELECT 1 FROM receipts)
BEGIN
    INSERT INTO receipts (user_id, receipt_date) VALUES
        (1, DATEADD(DAY, -1, SYSUTCDATETIME())),
        (1, DATEADD(DAY, -3, SYSUTCDATETIME())),
        (1, DATEADD(DAY, -7, SYSUTCDATETIME())),
        (2, DATEADD(DAY, -2, SYSUTCDATETIME()));
END
GO

-- Sample Reception Products
IF NOT EXISTS (SELECT 1 FROM reception_products)
BEGIN
    INSERT INTO reception_products (receipts_id, products_id, amount) VALUES
        (1, 1, 2),
        (1, 3, 1),
        (1, 5, 3),
        (2, 1, 1),
        (2, 8, 2),
        (2, 9, 1),
        (3, 1, 2),
        (3, 3, 1),
        (3, 7, 5),
        (3, 11, 1),
        (4, 2, 1),
        (4, 12, 2);
END
GO

-- Sample Product Ranges for Users
IF NOT EXISTS (SELECT 1 FROM product_range_for_the_user)
BEGIN
    INSERT INTO product_range_for_the_user (user_id, Products_id, Range_id) VALUES
        (1, 1, 1),
        (1, 3, 1),
        (1, 9, 2),
        (2, 2, 1),
        (2, 12, 2);
END
GO

-- Sample Shopping List
IF NOT EXISTS (SELECT 1 FROM Shopping_list)
BEGIN
    INSERT INTO Shopping_list (Products_id, amount, Range_enum, user_id) VALUES
        (1, 2, 1, 1),
        (3, 1, 1, 1),
        (9, 1, 2, 1),
        (2, 1, 1, 2);
END
GO

-- Sample User_Product_Learning
IF NOT EXISTS (SELECT 1 FROM User_Product_Learning)
BEGIN
    INSERT INTO User_Product_Learning (user_id, product_id, learned_gap, confidence, samples_count, last_updated) VALUES
        (1, 1, 3.5, 0.85, 12, DATEADD(DAY, -1, SYSUTCDATETIME())),
        (1, 3, 1.2, 0.92, 15, DATEADD(DAY, -1, SYSUTCDATETIME())),
        (2, 2, 5.0, 0.60, 4, DATEADD(DAY, -2, SYSUTCDATETIME())),
        (2, 12, 7.0, 0.70, 8, DATEADD(DAY, -2, SYSUTCDATETIME()));
END
GO

PRINT '========================================'
PRINT 'SmartStock Demo Database Ready!'
PRINT '========================================'
GO
