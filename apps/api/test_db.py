import asyncio
import traceback
from app.db.session import AsyncSessionLocal
from app.repositories.student import StudentRepository

async def test_search():
    async with AsyncSessionLocal() as db:
        try:
            repo = StudentRepository(db)
            rows, total = await repo.search(page=1, page_size=20)
            print("SUCCESS!")
            print("Total:", total)
            print("Rows count:", len(rows))
            if rows:
                print("Sample row:", rows[0])
        except Exception as e:
            print("EXCEPT TYPE:", type(e))
            print("EXCEPT STR:", str(e))
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())
