from retriever import get_collection
from config import GAMES

col = get_collection()


print(f"{col.count()} chunks")

for g in GAMES:
    result = col.get(where={"game": g}, limit=1, include=["documents", "metadatas"])
    print(
        f"\n=== {result['ids'][0]}  (game: {result['metadatas'][0]['game']}) (len: {len(result['documents'][0])}) ==="
    )
    print(result["documents"][0])
