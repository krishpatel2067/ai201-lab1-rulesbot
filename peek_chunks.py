from retriever import get_collection

col = get_collection()


games = [
    "Catan",
    "Clue",
    "Codenames",
    "Monopoly",
    "Pandemic",
    "Risk",
    "Ticket To Ride",
    "Uno",
]

print(f"{col.count()} chunks")

for g in games:
    result = col.get(where={"game": g}, limit=1, include=["documents", "metadatas"])
    print(
        f"\n=== {result['ids'][0]}  (game: {result['metadatas'][0]['game']}) (len: {len(result['documents'][0])}) ==="
    )
    print(result["documents"][0])
