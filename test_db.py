import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    cursor.execute("SELECT version();")
    result = cursor.fetchone()

    print("Supabase PostgreSQL connected successfully!")
    print(result[0])

    cursor.close()
    conn.close()

except Exception as e:
    print("Database connection failed:")
    print(e)