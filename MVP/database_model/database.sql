CREATE TABLE "order" (
  "id" integer PRIMARY KEY,
  "user_id" integer NOT NULL,
  "bike_id" integer NOT NULL,
  "discount_id" integer,
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

CREATE TABLE "discounts" (
  "id" integer PRIMARY KEY,
  "value" float NOT NULL,
  "starts_at" timestamp NOT NULL,
  "ends_at" timestamp NOT NULL,
  "active" bool DEFAULT false
);

ALTER TABLE "order" ADD CONSTRAINT "discout_order" FOREIGN KEY ("discount_id") REFERENCES "discounts" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "order" ADD CONSTRAINT "user_order" FOREIGN KEY ("user_id") REFERENCES "users" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "order" ADD CONSTRAINT "bike_order" FOREIGN KEY ("bike_id") REFERENCES "bikes" ("id") DEFERRABLE INITIALLY IMMEDIATE;
