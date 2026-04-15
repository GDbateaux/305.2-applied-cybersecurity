CREATE TABLE "order" (
  "id" integer PRIMARY KEY,
  "user_id" integer NOT NULL,
  "bike_id" integer NOT NULL,
  "total_price" float NOT NULL,
  "validate" bool DEFAULT false,
  "order_at" timestamp NOT NULL DEFAULT (now())
);

CREATE TABLE "bikes" (
  "id" integer PRIMARY KEY,
  "name" varchar NOT NULL,
  "price" float NOT NULL,
  "maintenance_time" time NOT NULL
);

CREATE TABLE "users" (
  "id" integer PRIMARY KEY,
  "username" varchar NOT NULL,
  "password" varchar NOT NULL,
  "created_at" timestamp NOT NULL DEFAULT (now())
);

CREATE TABLE "stock_bikes" (
  "id" integer PRIMARY KEY,
  "bike_id" integer NOT NULL,
  "number" integer
);

ALTER TABLE "stock_bikes" ADD CONSTRAINT "stock_bikes" FOREIGN KEY ("bike_id") REFERENCES "bikes" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "order" ADD CONSTRAINT "user_order" FOREIGN KEY ("user_id") REFERENCES "users" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "order" ADD CONSTRAINT "bike_order" FOREIGN KEY ("bike_id") REFERENCES "bikes" ("id") DEFERRABLE INITIALLY IMMEDIATE;
