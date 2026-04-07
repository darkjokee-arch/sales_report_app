import sqlite3

def migrate():
    conn = sqlite3.connect('sales_db.sqlite')
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE reports ADD COLUMN kapt_code TEXT DEFAULT ''")
        print("kapt_code column added.")
    except Exception as e:
        print(f"kapt_code add error (might exist): {e}")

    try:
        c.execute("ALTER TABLE reports ADD COLUMN long_term_reserve TEXT DEFAULT ''")
        print("long_term_reserve column added.")
    except Exception as e:
        print(f"long_term_reserve add error (might exist): {e}")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    migrate()
