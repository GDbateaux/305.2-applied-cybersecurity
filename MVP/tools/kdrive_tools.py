import os
from threading import local
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

BASE_DIRECTORY_ID="72"

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
    result = list_information_files_in_folder(BASE_DIRECTORY_ID)
    if isinstance(result, str):
        return result

    patient_directory_id = None
    for file in result:
        if file["name"] == str(patient_id) and file["type"] == "dir":
            patient_directory_id = file["id"]
            break

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

    local_dir = Path(__file__).parent.parent / "kdrive_cache" / str(patient_id)
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
    
def download_file_unrestricted(file_id: str):
    meta_url = f"{BASE_URL}/3/drive/{DRIVE_ID}/files/{file_id}"
    try:
        response = requests.get(meta_url, headers=HEADERS)
        response.raise_for_status()
        file_obj = response.json().get("data", {})
    except requests.exceptions.RequestException as e:
        return f"Error retrieving file metadata: {e}"

    if file_obj.get("type") == "dir":
        return "Error: Cannot download a directory."

    filename = file_obj.get("name", f"{file_id}.bin")

    local_dir = Path(__file__).parent.parent / "kdrive_cache" / "doctor"
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


def build_kdrive_tools(patient_id: str | None):

    def list_files_for_context(target_patient_id: str | None = None):
        if patient_id is None and target_patient_id is None:
            folders = list_information_files_in_folder(BASE_DIRECTORY_ID)
            if isinstance(folders, str):
                return folders
            return [f for f in folders if f["type"] == "dir"]
        else:
            pid = patient_id or target_patient_id
            return list_files_for_patient(pid)

    def download_file_for_context(file_id: str):
        if patient_id is None:
            return download_file_unrestricted(file_id)
        else:
            return download_file(patient_id, file_id)

    if patient_id is not None:
        @tool
        def search_kdrive() -> str:
            """Lists all documents available in your personal medical folder.
            Always call this first to get file IDs before reading a file."""
            files = list_files_for_context()
            if isinstance(files, str):
                return files
            if not files:
                return "No files found."
            return "\n".join(f"- {f['name']} (id: {f['id']}, type: {f['type']})" for f in files)

    else:
        @tool
        def search_kdrive(target_patient_id: str = "") -> str:
            """Lists available documents in kDrive.
            - Without argument: lists all patient folders.
            - With a patient_id: lists files inside that specific patient's folder.
            Always use get_patient_id_by_name first if you only have a patient name.
            Parameter: target_patient_id (optional, leave empty to list all patient folders)."""
            files = list_files_for_context(target_patient_id or None)
            if isinstance(files, str):
                return files
            if not files:
                return "No files found."
            return "\n".join(f"- {f['name']} (id: {f['id']}, type: {f['type']})" for f in files)

    @tool
    def read_kdrive_file(file_id: str) -> str:
        """Reads the contents of a kDrive file by its ID.
        Supports: .txt, .csv, .pdf, .docx, .xlsx.
        Use this after search_kdrive to read a specific file.
        Parameter: file_id (the ID returned by search_kdrive)."""
        local_path = download_file_for_context(file_id)
        if isinstance(local_path, str) and local_path.startswith("Error"):
            return f"Download error: {local_path}"
        return extract_text(local_path)

    @tool
    def summarize_and_store_feedback(content: str, author: str, project: str) -> str:
        """Summarizes patient feedback and stores it in kDrive.
        ALWAYS call this immediately when a message contains a review, complaint, or suggestion.
        Do NOT promise to save — just call this tool directly.
        Parameters: content (message), author (Telegram ID or name),
        project (topic; use 'general' if unknown)."""
        now = datetime.now()
        filename = f"feedback_{author}_{now.strftime('%Y-%m-%d_%H-%M')}.txt"
        summary = (
            f"Date: {now.strftime('%Y-%m-%d %H:%M')}\n"
            f"Author: {author}\n"
            f"Project: {project}\n\n"
            f"Content:\n{content}\n"
        )
        result = upload_message_summary_KDrive(summary, filename)
        if result:
            return f"Feedback stored in kDrive as '{filename}'."
        return f"Error storing feedback: {result}"

    return [search_kdrive, read_kdrive_file, summarize_and_store_feedback]
