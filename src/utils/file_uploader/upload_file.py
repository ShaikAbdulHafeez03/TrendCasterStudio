from supabase import create_client
import os

SUPABASE_URL = "https://rmkbwjjeegmxwqpmqzpw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJta2J3amplZWdteHdxcG1xenB3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mjg0ODczNCwiZXhwIjoyMDc4NDI0NzM0fQ.WfORcTLVNx0YDxwIk-yqUJQjsP6FuE3DgWKc43esnX8"
BUCKET_NAME = "social_automator"


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_file(file_path: str):
    """Uploads a file to Supabase Storage and returns its public URL."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return None

    file_name = os.path.basename(file_path)
    dest_path = f"videos/{file_name}"

    print(f"📤 Uploading {file_name} → {BUCKET_NAME}/{dest_path}")

    with open(file_path, "rb") as f:
        result = supabase.storage.from_(BUCKET_NAME).upload(
            path=dest_path,
            file=f,
            file_options={"x-upsert": "true"},
        )

    if hasattr(result, "error") and result.error:
        print("❌ Upload failed:", result.error)
        return None

    print("✅ Upload successful!")


    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(dest_path)
    print("🌐 Public URL:", public_url)
    return public_url


if __name__ == "__main__":
    file_path = "output.mp4"  
    upload_file(file_path)
