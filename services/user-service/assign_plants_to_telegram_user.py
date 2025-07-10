import db

# Find the first non-default user (assume this is the Telegram user)
with db.get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT id, telegram_id, name FROM users WHERE telegram_id != 'default_telegram_id' ORDER BY id LIMIT 1")
    user = c.fetchone()
    if not user:
        print("No Telegram user found. Please use the bot at least once to register.")
        exit(1)
    user_id = user[0]
    print(f"Assigning all plants to user_id {user_id} (telegram_id={user[1]}, name={user[2]})")
    c.execute("UPDATE plants SET user_id = ?", (user_id,))
    conn.commit()
    print("All plants assigned to your Telegram user.") 