-- Schema básico para testes de analytics (idempotente)
CREATE SCHEMA IF NOT EXISTS demo;

CREATE TABLE IF NOT EXISTS demo.customers (
  customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name        TEXT NOT NULL,
  email       TEXT UNIQUE,
  city        TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS demo.products (
  product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sku        TEXT NOT NULL UNIQUE,
  name       TEXT NOT NULL,
  category   TEXT,
  unit_price NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
  active     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS demo.orders (
  order_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ext_code     TEXT UNIQUE,
  customer_id  BIGINT NOT NULL REFERENCES demo.customers(customer_id) ON DELETE RESTRICT,
  order_date   TIMESTAMPTZ NOT NULL DEFAULT now(),
  status       TEXT NOT NULL CHECK (status IN ('NEW','PAID','CANCELLED','SHIPPED')),
  total_amount NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0)
);

CREATE TABLE IF NOT EXISTS demo.order_items (
  order_item_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  order_id      BIGINT NOT NULL REFERENCES demo.orders(order_id) ON DELETE CASCADE,
  product_id    BIGINT NOT NULL REFERENCES demo.products(product_id) ON DELETE RESTRICT,
  qty           INTEGER NOT NULL CHECK (qty > 0),
  unit_price    NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
  line_total    NUMERIC(14,2) GENERATED ALWAYS AS (qty * unit_price) STORED,
  UNIQUE(order_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_orders_customer      ON demo.orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order    ON demo.order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_products_category    ON demo.products(category);

-- Dimensão de datas resumida (últimos 10 dias)
CREATE TABLE IF NOT EXISTS demo.dim_date (
  d DATE PRIMARY KEY,
  year INT, month INT, day INT,
  month_name TEXT
);
INSERT INTO demo.dim_date (d, year, month, day, month_name)
SELECT d::date,
       EXTRACT(YEAR FROM d)::int,
       EXTRACT(MONTH FROM d)::int,
       EXTRACT(DAY FROM d)::int,
       TO_CHAR(d,'TMMonth')
FROM generate_series((now() - interval '9 day')::date, now()::date, interval '1 day') g(d)
ON CONFLICT (d) DO NOTHING;

-- Seeds (idempotentes)
INSERT INTO demo.customers (name,email,city) VALUES
  ('Ana Silva','ana@exemplo.com','São Paulo'),
  ('Bruno Costa','bruno@exemplo.com','Rio de Janeiro'),
  ('Carla Dias','carla@exemplo.com','Curitiba')
ON CONFLICT (email) DO NOTHING;

INSERT INTO demo.products (sku,name,category,unit_price) VALUES
  ('SKU-100','Teclado Mecânico','Periféricos',350.00),
  ('SKU-200','Mouse Óptico','Periféricos',120.00),
  ('SKU-300','Monitor 27"','Displays',1599.90),
  ('SKU-400','Headset USB','Áudio',299.00),
  ('SKU-500','Dock USB-C','Acessórios',499.00)
ON CONFLICT (sku) DO NOTHING;

-- Orders com ext_code para idempotência
WITH c AS (
  SELECT email, customer_id FROM demo.customers
), toins AS (
  SELECT * FROM (VALUES
    ('ORD-0001', now() - interval '2 day', 'NEW',  'ana@exemplo.com'),
    ('ORD-0002', now() - interval '1 day', 'PAID', 'bruno@exemplo.com'),
    ('ORD-0003', now(),                   'PAID', 'carla@exemplo.com')
  ) v(ext_code, order_date, status, email)
)
INSERT INTO demo.orders (ext_code, customer_id, order_date, status, total_amount)
SELECT t.ext_code, c.customer_id, t.order_date, t.status, 0
FROM toins t JOIN c ON c.email = t.email
ON CONFLICT (ext_code) DO NOTHING;

DO $$
DECLARE
  o1 BIGINT; o2 BIGINT; o3 BIGINT;
  p100 BIGINT; p200 BIGINT; p300 BIGINT; p400 BIGINT; p500 BIGINT;
  up100 NUMERIC; up200 NUMERIC; up300 NUMERIC; up400 NUMERIC; up500 NUMERIC;
BEGIN
  SELECT order_id INTO o1 FROM demo.orders WHERE ext_code='ORD-0001';
  SELECT order_id INTO o2 FROM demo.orders WHERE ext_code='ORD-0002';
  SELECT order_id INTO o3 FROM demo.orders WHERE ext_code='ORD-0003';

  SELECT product_id, unit_price INTO p100, up100 FROM demo.products WHERE sku='SKU-100';
  SELECT product_id, unit_price INTO p200, up200 FROM demo.products WHERE sku='SKU-200';
  SELECT product_id, unit_price INTO p300, up300 FROM demo.products WHERE sku='SKU-300';
  SELECT product_id, unit_price INTO p400, up400 FROM demo.products WHERE sku='SKU-400';
  SELECT product_id, unit_price INTO p500, up500 FROM demo.products WHERE sku='SKU-500';

  IF o1 IS NOT NULL THEN
    INSERT INTO demo.order_items(order_id,product_id,qty,unit_price)
    VALUES (o1,p100,1,up100),(o1,p200,2,up200)
    ON CONFLICT (order_id,product_id) DO NOTHING;
  END IF;

  IF o2 IS NOT NULL THEN
    INSERT INTO demo.order_items(order_id,product_id,qty,unit_price)
    VALUES (o2,p300,1,up300)
    ON CONFLICT (order_id,product_id) DO NOTHING;
  END IF;

  IF o3 IS NOT NULL THEN
    INSERT INTO demo.order_items(order_id,product_id,qty,unit_price)
    VALUES (o3,p400,1,up400),(o3,p500,1,up500)
    ON CONFLICT (order_id,product_id) DO NOTHING;
  END IF;
END $$;

-- Recalcular total dos pedidos
UPDATE demo.orders o
SET total_amount = COALESCE(s.sum_total,0)
FROM (
  SELECT order_id, SUM(line_total) AS sum_total
  FROM demo.order_items GROUP BY order_id
) s
WHERE o.order_id = s.order_id;

-- Views rápidas
CREATE OR REPLACE VIEW demo.v_order_summary AS
SELECT o.order_id, o.ext_code, c.name AS customer, o.order_date, o.status, o.total_amount
FROM demo.orders o JOIN demo.customers c ON c.customer_id = o.customer_id;

CREATE OR REPLACE VIEW demo.v_customer_ltv AS
SELECT c.customer_id, c.name, COALESCE(SUM(o.total_amount),0) AS lifetime_value
FROM demo.customers c LEFT JOIN demo.orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
ORDER BY lifetime_value DESC;