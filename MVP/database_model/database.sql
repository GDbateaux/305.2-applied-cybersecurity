CREATE TABLE "patients" (
  "id" int PRIMARY KEY,
  "telegram_id" bigints NOT NULL,
  "doctor_id" bigint NOT NULL,
  "name" varchar NOT NULL,
  "surname" varchar NOT NULL
);

CREATE TABLE "doctors" (
  "id" int PRIMARY KEY,
  "telegram_id" bigints NOT NULL,
  "name" varchar NOT NULL,
  "surname" varchar NOT NULL
);

ALTER TABLE "doctors" ADD CONSTRAINT "patient_doctor" FOREIGN KEY ("id") REFERENCES "patients" ("doctor_id") DEFERRABLE INITIALLY IMMEDIATE;
