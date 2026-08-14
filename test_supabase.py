import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print("Supabase URL:", url)

if not url or not key:
    print("ERROR: .env values are missing")
    exit()

try:
    supabase = create_client(url, key)

    # Test your invoices table
    response = supabase.table("invoices").select("*").limit(1).execute()

    print("================================")
    print("SUPABASE CONNECTION SUCCESSFUL")
    print("================================")
    print("Data returned:", response.data)

except Exception as e:
    print("================================")
    print("SUPABASE CONNECTION FAILED")
    print("================================")
    print("Error:", e)