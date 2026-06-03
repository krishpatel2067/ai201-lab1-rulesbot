# Spec: `retrieve()`

**File:** `retriever.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Given a user's natural language query, find the most relevant chunks from the vector store using semantic similarity search. Return them ranked by relevance so that `generate_response()` can use them as context.

---

## Input / Output Contract

**Inputs:**

| Parameter   | Type  | Description                                                                |
| ----------- | ----- | -------------------------------------------------------------------------- |
| `query`     | `str` | The user's natural language question                                       |
| `n_results` | `int` | Maximum number of chunks to return (default: `N_RESULTS` from `config.py`) |

**Output:** `list[dict]`

Each dict in the returned list must contain exactly these keys:

| Key          | Type    | Description                                                   |
| ------------ | ------- | ------------------------------------------------------------- |
| `"text"`     | `str`   | The chunk text                                                |
| `"game"`     | `str`   | The game name this chunk came from                            |
| `"distance"` | `float` | Cosine distance score — lower means more similar to the query |

Results should be ordered from most to least relevant (lowest to highest distance). Returns an empty list `[]` if the collection contains no documents.

---

## Design Decisions

_Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours._

---

### Query approach ☑️

_Describe how you will use `_collection.query()` to find relevant chunks. What arguments will you pass, and why?_

```
_collection.query() needs the actual query, the number of results to return, and the fields to include in the return value:

_collection.query(
    query_texts=["query1"],
    n_results=N_RESULTS,
    include=["documents", "metadatas", "distances"]
)

A concrete example of query()'s return value:

 {
    "ids": [
        ["uno_007", "uno_012", "catan_003"]
    ],
    "documents": [
        [
            "Each player is dealt seven cards to start the game.",
            "On your turn, if you cannot play a card, draw one from the deck.",
            "Players collect resource cards based on the dice roll each turn."
        ]
    ],
    "metadatas": [
        [
            {"game": "Uno"},
            {"game": "Uno"},
            {"game": "Catan"}
        ]
    ],
    "distances": [
        [0.1834, 0.4021, 0.7765]
    ],
    "embeddings": None,
    "uris": None,
    "data": None,
    "included": ["documents", "metadatas", "distances"]
}

Each outer list is for each query (1 in our case), and each inner list holds the top-k results.
```

---

### Return structure ☑️

_Sketch out what one item in your return list looks like as a concrete example. Where does each field come from in the query results?_

```
The return list contains dictionaries, each of which follows this structure:
[
    {
        "text": "Each player is dealt seven cards to start the game.",  # from documents[0][i]
        "game": "Uno",                                                  # from metadatas[0][i]["game"]
        "distance": 0.1834,                                             # from distances[0][i]
    },
    ...
]
```

---

### Handling the nested result structure ☑️

_`_collection.query()` returns nested lists. Describe what index you need to access to get the actual list of results for a single query, and why the nesting exists._

```
The nested structure exists to handle multiple queries (e.g. query_texts=["text1", "text2", ...]). Because we will only be passing one query at a time, we will always index the outer list of the query's result with 0 to access the inner list of top-k results for the documents, metadatas, and distances fields.
```

---

### Relevance threshold ☑️

_Will you filter out results above a certain distance score, or return all `n_results` regardless of how relevant they are? What are the tradeoffs of each approach?_

```
Filtering out results above a certain distance helps the final answers be relevant as well as reduce hallucinations by shielding the LLM from irrelevant sources. However, sometimes the distance scoring may be too high despite actual relevance, causing edge cases where certain relevant answers never get returned. Another issue is that hardcoding a threshold value is unreliable if the embedding model and/or corpora change. On the flip side, returning all n_results regardless of distance solves the false negative shortcoming by always including the sources even with erroneous distance scores. However, now the problem is that the LLM may struggle to reconcile irrelevant sources with its system prompt of choosing the "best" one. In this case, the system prompt should be modified to allow the LLM a "way out," stating that no relevant answers could be found. This in itself presents a new challenge: making sure that the LLM does not use that escape too often, which would render RulesBot useless.

In light of these advantages and disadvantages, I will opt for a "hybrid" solution: setting a high (permissive) distance threshold to allow almost all results through except those that are almost certainly irrelevant. I performed some testing via peek_query_results.py to decide the threshold value. The results (given in query_results.txt) indicate a narrow band between the worst relevant-query result of 0.588 and the best off-topic-query result of 0.609 (tested with tricky adversarial cases too). Thus, a reasonable and round threshold value is 0.60. Because the band gap is thin, this threshold value should be paired with the LLM's escape hatch of "no relevant answers found" just in case there are any false positives.

Things to note:

* The threshold's false negatives (eliminating high-distance relevant answers) never pass to the LLM, preventing it from answering a question that could have been answered.
* The experiment script used a small sample set (~20). Real user queries may be even trickier due to higher vagueness, filler words, typos, etc., causing the real threshold to drift and rendering this hardcoded one stale.
```

---

### Edge cases ☑️

_How does your implementation behave when: (a) the collection is empty, (b) the query matches no chunks well, (c) the query matches chunks from multiple games?_

```
(a) The given code already handles an empty collection by returning an empty list.
(b) If all the chunks fall below the hardcoded threshold, the LLM's escape hatch should hopefully catch them all as irrelevant. If they are filtered out by the threshold, then the LLM gets no chunks to retrieve from and should certainly indicate that no relevant chunks were found.
(c) When the query matches chunks from multiple games, the current retriever still passes all k results to the LLM because the current algorithm doesn't group by the game. However, for user queries that explicitly name a game, we can scope the query using where={"game": ...} to only get game-relevant chunks. One thing to note here is that the metadata matching requires an exact match, so abbreviations, typos, and different capitalizations of game names may get missed in user queries. An advanced fix is to use an LLM to get the game name, but that is beyond the scope of this lab!
```

---

## Implementation Notes

_Fill this in after implementing, before moving to Milestone 3._

**Test query and top result returned:**

```
Query: [your test query]
Top result game: [game name]
Distance score: [score]
Does it make sense? [yes / no / explain]
```

**One thing about the query results that surprised you:**

```
[your answer here]
```
