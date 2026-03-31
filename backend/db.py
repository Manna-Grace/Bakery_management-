import mysql.connector   # ✅ THIS LINE IS MISSING

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="whiff_whisk"
    )