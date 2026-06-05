from motor.motor_asyncio import AsyncIOMotorDatabase


class DrugMatcher:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def match(self, medications: list):
        results = []

        for med in medications:
            name = med.get("name")

            product = await self.db.products.find_one({
                "name": {"$regex": name, "$options": "i"}
            })

            results.append({
                "input": med,
                "match": product
            })

        return results