import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from app.static.config import DATABASE_URL


def test_connection():
    print("1. Testing connection...")
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    print("   Connected to:", DATABASE_URL.split("@")[1].split("?")[0])
    
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print("   PostgreSQL version:", version.split(",")[0])

    print("\n2. Creating table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loan_applications (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            submission_timestamp TIMESTAMP NOT NULL,
            personal_info JSONB,
            financial_info JSONB,
            employment_info JSONB,
            uploaded_documents JSONB,
            financial_metrics JSONB,
            all_documents_uploaded BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    print("   Table 'loan_applications' ready.")

    print("\n3. Inserting test record...")
    cursor.execute("""
        INSERT INTO loan_applications (
            user_id, submission_timestamp, personal_info, financial_info,
            employment_info, uploaded_documents, financial_metrics, all_documents_uploaded
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        "db_test_user",
        datetime.now(),
        Json({"name": "Test User", "age": 30}),
        Json({"net_monthly_income": 80000}),
        Json({"employer_name": "Test Corp"}),
        Json({"pan": {"uploaded": True}}),
        Json({"cibil_score": 750}),
        False
    ))
    record_id = cursor.fetchone()[0]
    conn.commit()
    print("   Inserted with ID:", record_id)

    print("\n4. Reading back...")
    cursor.execute("SELECT id, user_id, personal_info FROM loan_applications WHERE id = %s", (record_id,))
    row = cursor.fetchone()
    print("   ID:", row[0], "| User:", row[1], "| Name:", row[2]["name"])

    print("\n5. Cleaning up test record...")
    cursor.execute("DELETE FROM loan_applications WHERE id = %s", (record_id,))
    conn.commit()
    print("   Deleted.")

    cursor.close()
    conn.close()
    print("\n All checks passed! Database is ready.")


if __name__ == "__main__":
    try:
        test_connection()
    except Exception as e:
        print(f"\n Failed: {e}")
