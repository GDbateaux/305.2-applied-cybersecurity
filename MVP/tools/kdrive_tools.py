import os
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from datetime import datetime
from pathlib import Path
from tools.file_utils import extract_text

load_dotenv()
DRIVE_ID = os.getenv("KDRIVE_DRIVE_ID")
TOKEN = os.getenv("KDRIVE_TOKEN")
BASE_URL = f"https://api.infomaniak.com"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def list_information_files_in_folder(folder_id: str):
    url = f"{BASE_URL}/3/drive/{DRIVE_ID}/files/{folder_id}/files"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json().get("data", [])
        files_summary = [
            {"name": f["name"], "id": f["id"], "type": f["type"], "size": f.get("size")}
            for f in data
        ]
        return files_summary
    except requests.exceptions.RequestException as e:
        return f"Error listing files: {e}"

# Helpers for kDrive interactions
def list_files_for_patient(patient_id: str):
    base_directory_id="72"

    result = list_information_files_in_folder(base_directory_id)
    if isinstance(result, str):
        return result
    
    for file in result:
        if file["name"] == patient_id and file["type"] == "dir":
            patient_directory_id = file["id"]

    if not patient_directory_id:
        return f"No directory found for ID {patient_id}."

    return list_information_files_in_folder(patient_directory_id)


def download_file(patient_id: str, file_id: str):
    patient_files = list_files_for_patient(patient_id)

    if isinstance(patient_files, str):
        return patient_files
    
    file_obj = next((f for f in patient_files if str(f["id"]) == file_id), None)

    if not file_obj:
        return f"Error: File {file_id} not found in patient {patient_id} directory."

    if file_obj["type"] == "dir":
        return "Error: Cannot download a directory."

    filename = file_obj["name"]

    local_dir = Path(__file__).parent.parent / "kdrive_cache"
    local_dir.mkdir(parents=True, exist_ok=True)

    local_path = local_dir / filename
    download_url = f"{BASE_URL}/2/drive/{DRIVE_ID}/files/{file_id}/download"
    try:
        response = requests.get(download_url, headers=HEADERS, stream=True)
        response.raise_for_status()

        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        return local_path
    except requests.exceptions.RequestException as e:
        return f"Error downloading file: {e}"


def upload_message_summary_KDrive(text_content, filename="uploaded_file.txt"):
    destination_id="38"
    url = f"{BASE_URL}/3/drive/{DRIVE_ID}/upload"

    encoded_content = text_content.encode("utf-8")
    total_size = len(encoded_content)

    params = {
        "directory_id": int(destination_id),
        "file_name": filename,
        "total_size": total_size,
        "conflict": "rename"
    }

    response = requests.post(
        url,
        headers={"Authorization": HEADERS["Authorization"]},
        params=params,
        data=encoded_content
    )

    if not response.ok:
        raise Exception(f"Failed to upload file: {response.status_code} {response.text}")
    return True


@tool
def read_kdrive_file(patient_id: str, file_id: str) -> str:
    """Reads the contents of a kDrive file by its ID.
    Supports: .txt, .csv, .pdf, .docx, .xlsx.
    Use this after search_kdrive to read a specific file.
    Parameter: file_id (the ID returned by search_kdrive)."""
    local_path = download_file(patient_id, file_id)
    if isinstance(local_path, str) and local_path.startswith("Error"):
        return f"Download error: {local_path}"
    return extract_text(local_path)


@tool
def summarize_and_store_feedback(patient_id: str, content: str, author: str, project: str) -> str:
    """Summarizes customer feedback and stores it in kDrive.
    ALWAYS call this immediately when a message contains a review, complaint, or suggestion.
    Do NOT promise to save — just call this tool directly.
    Parameters: content (customer message), author (Telegram ID or name),
    project (product or topic; use 'general' if unknown)."""
    now = datetime.now()
    filename = f"feedback_{author}_{now.strftime('%Y-%m-%d_%H-%M')}.txt"
    summary = (
        f"Date: {now.strftime('%Y-%m-%d %H:%M')}\n"
        f"Author: {author}\n"
        f"Project: {project}\n\n"
        f"Content:\n{content}\n"
    )
    result = upload_message_summary_KDrive(patient_id, summary, filename)
    if result:
        return f"Feedback stored in kDrive as '{filename}'."
    return f"Error storing feedback: {result}"
