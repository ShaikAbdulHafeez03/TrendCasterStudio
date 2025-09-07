from google.cloud import storage
bucket_name = "social_automator"
# destination_blob_name = "videos/226795_small.mp4" 
service_account_path = "src/credentials/zinc-direction-468404-e2-dd6fc221d3e0.json"  


def upload_to_gcs(source_file_path,bucket_name=bucket_name , service_account_path=service_account_path):
    import os
    filename = os.path.basename(source_file_path)
    destination_blob_name = f"videos/{filename}"
    client = storage.Client.from_service_account_json(service_account_path)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)
    blob.make_public()
    return blob.public_url

# print(upload_to_gcs("src/assets/social_post_1757281580_md9qop_3bd55e_1.png"))