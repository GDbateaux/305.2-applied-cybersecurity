import os
import requests
from dotenv import load_dotenv

load_dotenv()

class KDriveTools:
    def __init__(self, drive_id=None):
        self.drive_id = drive_id or os.getenv("KDRIVE_DRIVE_ID")
        self.token = os.getenv("KDRIVE_TOKEN")
        self.base_url = f"https://api.infomaniak.com"
        self.headers = {"Authorization": f"Bearer {self.token}"}

        if not self.drive_id:
            raise ValueError("DRIVE_ID is missing. Please set it in .env or pass it to the class.")

    def list_information_for_customers_files(self):
        """
        USE THIS TOOL FIRST to browse available documentation about customers.
        It lists all files inside the 'Customer Information' directory.
        
        Returns:
            list: A list of dictionaries with file 'name' and 'id'. 
                  Use these IDs to download specific files later.
        """
        directory_id="42"
        url = f"{self.base_url}/3/drive/{self.drive_id}/files/{directory_id}/files"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json().get("data", [])
            
            files_summary = [
                {"name": f["name"], "id": f["id"], "type": f["type"], "size": f.get("size")} 
                for f in data
            ]
            return files_summary
        except requests.exceptions.RequestException as e:
            return f"Error listing files: {e}"

    def download_file(self, file_id: str):
        """
        USE THIS TOOL to read the actual content of a file found via 'list_information_for_customers_files'.
        This downloads the file locally so you can process its information.
        
        Args:
            file_id (str): The unique ID of the file to download.
            
        Returns:
            str: The local file path. You must then open this path to read the content.
        """
        meta_url = f"{self.base_url}/3/drive/{self.drive_id}/files/{file_id}"

        try:
            response = requests.get(meta_url, headers=self.headers)
            response.raise_for_status()

            data = response.json().get("data", {})

            if data.get("type") == "dir":
                return "Error: Cannot download a directory."

            filename = data.get("name", f"{file_id}.bin")

        except requests.exceptions.RequestException as e:
            return f"Error retrieving file name: {e}"

        local_dir = "kdrive_cache"
        os.makedirs(local_dir, exist_ok=True)

        local_path = os.path.join(local_dir, filename)

        download_url = f"{self.base_url}/2/drive/{self.drive_id}/files/{file_id}/download"

        try:
            response = requests.get(download_url, headers=self.headers, stream=True)
            response.raise_for_status()

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

            return local_path

        except requests.exceptions.RequestException as e:
            return f"Error downloading file: {e}"

    def upload_message_summary(self, text_content, filename="uploaded_file.txt"):
        """
        USE THIS TOOL to save a summary of an email or conversation to kDrive.
        The file will be automatically saved in the 'Summaries' directory.
        
        Args:
            text_content (str): The summary or text to save.
            filename (str): Name of the file (e.g., 'meeting_summary_date.txt').
            
        Returns:
            str: Confirmation message with the new file ID.
        """
        destination_id="38"
        url = f"{self.base_url}/3/drive/{self.drive_id}/upload"

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
            headers={"Authorization": self.headers["Authorization"]},
            params=params,
            data=encoded_content
        )

        if not response.ok:
            return f"Upload failed: {response.status_code} - {response.text}"

        result = response.json()
        return f"OK: {result}"
    
if __name__ == "__main__":
    tools = KDriveTools()

    print(tools.list_information_for_customers_files())
    print(tools.upload_message_summary("Hello World from LLM", "ai_note.txt"))
    print(tools.download_file("39"))
