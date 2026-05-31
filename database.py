import aiosqlite

class Database:
    def __init__(self, path: str = "responses.db"):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    aroma TEXT,
                    like_score INTEGER,
                    bright_score INTEGER,
                    room TEXT,
                    variant TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                await db.execute("ALTER TABLE responses ADD COLUMN variant TEXT")
            except Exception:
                pass
            await db.commit()

    async def save_response(self, user_id, username, aroma, like=None, bright=None, room=None, variant=None):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO responses
                   (user_id, username, aroma, like_score, bright_score, room, variant)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, username, aroma, like, bright, room, variant)
            )
            await db.commit()
