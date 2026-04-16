# Dring dring chat bot

## Database Initialization

### Prerequisites

Before starting, make sure you have installed:

* [uv](https://github.com/astral-sh/uv)

* [Docker](https://www.docker.com/)

### Start the PostgreSQL Database

Run a PostgreSQL container using Docker:

```bash
docker run --name medi-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -e POSTGRES_DB=medical_db \
  -p 5432:5432 \
  -d postgres
```

---

### Environment Variables

Create a `.env` file at the root of the project:

```env
DATABASE_URL=postgresql://postgres:mysecretpassword@localhost:5432/medi_db
```

---

### Install Dependencies

Using `uv`:

```bash
uv sync
```

---

### Initialize the Database

To create all tables, run:

```bash
uv run database_model/models.py
```

If you want to create tables and populate with initial data you can run:

```bash
uv run database_model/seed.py
```

---

### Reset the Database (Optional)

To completely reset the database:

```bash
docker stop medi-db
docker rm medi-db
```

Then restart it using the previous Docker command.

---

### Notes

* The seed script is meant for development/testing environments.
* Always ensure Docker is running before executing `seed.py`.
* Make sure your `.env` file matches the database credentials.
