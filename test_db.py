import asyncio
import asyncpg

async def test_connection():
    # Connect to the database
    conn = await asyncpg.connect(
        user='tournament_user',
        password='tournament_pass',
        database='tournament_db',
        host='localhost'
    )

    # Test query
    version = await conn.fetchval('SELECT version()')
    print(f"Connected to: {version}")

    # Test strategies table
    strategies = await conn.fetch('SELECT * FROM strategies')
    print("\nLoaded strategies:")
    for s in strategies:
        print(f"- {s['name']} ({s['docker_image']})")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
