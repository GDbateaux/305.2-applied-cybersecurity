# Medi Guide bot

## Access Without Local Setup

The bot is already deployed on Infomaniak.

You can access it directly here:
**[https://t.me/guide_medi_bot](https://t.me/guide_medi_bot)**

No local installation is required.

---

## Features

### Doctor

* View assigned patients (`get_patient_list`)
* Search a patient by name (`get_patient_id_by_name`)
* Access patient medical files (via kDrive)
* Read documents linked to patients

---

### Patient

* Access personal medical records (kDrive)
* Read documents (PDF, TXT, etc.)
* Ask medical questions (strictly based on their records)
* Request appointment slots
* Book appointments
* Contact their doctor (via message relay)

---

### Unregistered User

* View available doctors
* Register as a new patient

---

## Run the Project Locally

### Prerequisites

Before starting, make sure you have installed:

* [uv](https://github.com/astral-sh/uv)
* [Docker](https://www.docker.com/)

---

### Start the PostgreSQL Database

Run a PostgreSQL container using Docker:

```bash
docker run --name medi-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=mysecretpassword -e POSTGRES_DB=medi_db -p 5432:5432 -d postgres
```

---


### Environment Variables

The project requires several environment variables to configure external services, authentication, and database access.

Create a `.env` file at the root of the project using the provided `.env.example`.

---

#### Database Configuration

| Variable       | Description                                             |
| -------------- | ------------------------------------------------------- |
| `DB_USER`      | Username for the PostgreSQL database                    |
| `DB_PASSWORD`  | Password for the PostgreSQL database                    |
| `DB_NAME`      | Name of the PostgreSQL database                         |
| `DATABASE_URL` | Full database connection string used by the application |

---

#### External APIs & Services

| Variable                | Description                            |
| ----------------------- | -------------------------------------- |
| `KDRIVE_TOKEN`          | Authentication token for kDrive API    |
| `KDRIVE_DRIVE_ID`       | ID of the kDrive storage space         |
| `LLM_MODEL`             | Name of the model used for the chatbot |
| `INFOMANIAK_PRODUCT_ID` | Infomaniak product identifier          |
| `INFOMANIAK_API_KEY`    | API key for Infomaniak services        |

---

#### Calendar System

| Variable            | Description                  |
| ------------------- | ---------------------------- |
| `CALENDAR_USERNAME` | Username for calendar access |
| `CALENDAR_PASSWORD` | Password for calendar access |

---

#### Telegram Bot Configuration

| Variable                | Description                       |
| ----------------------- | --------------------------------- |
| `TELEGRAM_TOKEN`        | Telegram bot authentication token |
| `DOCTOR_1_TELEGRAM_ID`  | Telegram ID of doctor user        |
| `PATIENT_1_TELEGRAM_ID` | Telegram ID of test patient       |

---

### Install Dependencies

```bash
uv sync
```

---

### Run the Application

```bash
uv run main.py
```

👉 This will:

* Connect to the database
* Create tables if they do not exist
* Populate the database (if empty)
* Start the Telegram bot

---

### Notes

* Always ensure Docker is running before starting the app
* Make sure your `.env` file matches the database credentials

---

## Important

* Medical responses are strictly based on patient records
* No medical advice is generated outside stored data
* Patient data is strictly isolated and secure
