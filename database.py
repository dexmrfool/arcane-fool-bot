import asyncpg
import logging
import os
from config import DATABASE_URL

logger = logging.getLogger(__name__)

pool = None

async def init_db():
    global pool
    if not DATABASE_URL:
        logger.warning("DATABASE_URL is missing! Bot cannot save data.")
        return
        
    pool = await asyncpg.create_pool(DATABASE_URL)
    
    async with pool.acquire() as conn:
        # Create Users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                status TEXT DEFAULT 'pending',
                xp INTEGER DEFAULT 0,
                invite_count INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0,
                referrer_id BIGINT,
                join_time TIMESTAMP,
                last_message_time TIMESTAMP,
                last_message_text TEXT
            )
        ''')
        
        # Create Invites table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS invites (
                id SERIAL PRIMARY KEY,
                referrer_user_id BIGINT,
                invited_user_id BIGINT UNIQUE,
                status TEXT DEFAULT 'valid',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(referrer_user_id) REFERENCES users(id),
                FOREIGN KEY(invited_user_id) REFERENCES users(id)
            )
        ''')
        
        # Global status table for event state
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS globals (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Insert default global state if not exists
        await conn.execute("INSERT INTO globals (key, value) VALUES ('event_active', 'true') ON CONFLICT DO NOTHING")
        await conn.execute("INSERT INTO globals (key, value) VALUES ('gc_message_count', '0') ON CONFLICT DO NOTHING")
        
    logger.info("Database initialized with PostgreSQL.")

class DBCursor:
    def __init__(self, records):
        self.records = records

    async def fetchone(self):
        if not self.records:
            return None
        return tuple(self.records[0].values())

    async def fetchall(self):
        return [tuple(r.values()) for r in self.records] if self.records else []

class DBWrapper:
    def __init__(self, pool):
        self.pool = pool
        
    def _convert_query(self, query):
        parts = query.split('?')
        if len(parts) == 1:
            return query
        res = parts[0]
        for i, part in enumerate(parts[1:]):
            res += f"${i+1}" + part
        return res
        
    async def execute(self, query, args=()):
        query = self._convert_query(query)
        if query.strip().upper().startswith("SELECT"):
            async with self.pool.acquire() as conn:
                res = await conn.fetch(query, *args)
                return DBCursor(res)
        else:
            async with self.pool.acquire() as conn:
                await conn.execute(query, *args)
                return None
                
    async def commit(self):
        pass # asyncpg automatically commits

async def get_db():
    return DBWrapper(pool)

async def get_global(key, default=None):
    db = DBWrapper(pool)
    cursor = await db.execute("SELECT value FROM globals WHERE key = ?", (key,))
    row = await cursor.fetchone()
    if row:
        return row[0]
    return default

async def set_global(key, value):
    query = "INSERT INTO globals (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
    async with pool.acquire() as conn:
        await conn.execute(query, key, str(value))
