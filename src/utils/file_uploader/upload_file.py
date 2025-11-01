import os
from supabase import create_client, Client

# ✅ Replace these with your Supabase project details
SUPABASE_URL = "https://zgysyaxscrnkehvyehyl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpneXN5YXhzY3Jua2VodnllaHlsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTYzNjE1NSwiZXhwIjoyMDc3MjEyMTU1fQ.zPHu13XtBQyayj3EBbgxX9HA8mNX06eYRzfwQ5O2Ct4"
BUCKET_NAME = "socia_automator"

# Create the client object
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_to_gcs(source_file_path, bucket_name=BUCKET_NAME):
    """
    Uploads a file to a Supabase Storage bucket.
    """
    try:
        filename = os.path.basename(source_file_path)
        destination_blob_name = f"videos/{filename}"

        with open(source_file_path, "rb") as f:
            # The upload call will raise an exception if it fails
            supabase.storage.from_(bucket_name).upload(
                destination_blob_name,
                f,
                # ❗FIX: Pass upsert as a string header
                file_options={"x-upsert": "true"}
            )

        # If upload succeeded, get public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(destination_blob_name)
        
        print(f"Successfully uploaded to: {public_url}")
        return public_url
        
    except Exception as e:
        print(f"Upload failed: {e}")
        return None

# --- Example Usage ---
# if __name__ == "__main__":
#     # Create a dummy file to test
#     with open("test_upload.txt", "w") as f:
#         f.write("Hello Supabase!")
    
#     url = upload_to_supabase("test_upload.txt")
    
#     if url:
#         print(f"File URL: {url}")
#     else:
#         print("Upload failed.")