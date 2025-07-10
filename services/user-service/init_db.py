import db

def main():
    db.ensure_db()
    print("Database initialized and tables created.")
 
if __name__ == "__main__":
    main() 