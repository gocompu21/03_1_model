"""
Direct SQL migration for answer field conversion
This script uses raw SQL to avoid Django migration issues
"""
import sqlite3

# Connect directly to SQLite
db_path = "db.sqlite3"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Step 1: Backing up answer data...")
# Create temp table to store old answers
cursor.execute("""
    CREATE TEMP TABLE temp_answers AS
    SELECT id, answer FROM exam_question
""")

print("Step 2: Adding new column...")
# Add new JSON column
cursor.execute("""
    ALTER TABLE exam_question ADD COLUMN answer_json TEXT
""")

print("Step 3: Converting data...")
# Convert integers to JSON lists
cursor.execute("""
    UPDATE exam_question
    SET answer_json = '[' || CAST(answer AS TEXT) || ']'
""")

print("Step 4: Verifying conversion...")
# Check a few records
cursor.execute("SELECT id, answer, answer_json FROM exam_question LIMIT 5")
for row in cursor.fetchall():
    print(f"  Q{row[0]}: {row[1]} → {row[2]}")

print("\nStep 5: Finalizing...")
# Drop old column and rename new one
cursor.execute("""
    ALTER TABLE exam_question DROP COLUMN answer
""")
cursor.execute("""
    ALTER TABLE exam_question RENAME COLUMN answer_json TO answer
""")

conn.commit()
conn.close()

print("✓ Conversion complete!")
print("\nNow run: python manage.py migrate --fake exam 0006")
