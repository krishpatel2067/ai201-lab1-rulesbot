"""
Threshold-calibration script for retrieve().

Runs a fixed set of test queries against the vector store, prints the top-3
cosine distances for each, and summarizes them so we can pick a sensible
distance threshold empirically (rather than guessing).

The queries are split into two groups:
  - "relevant"  : good-faith rules questions spanning the ingested games.
                  These should score LOW (close matches exist).
  - "off-topic" : questions with no answer in any rulebook.
                  These should score HIGH (no good match) and calibrate the
                  ceiling — the point above which a result is almost certainly
                  noise.

The threshold we want lives in the gap between the WORST relevant distance and
the BEST off-topic distance. If those two overlap, no single clean threshold
separates signal from noise — which is itself worth knowing.

Run:  python peek_query_results.py
"""

from retriever import get_collection
from config import N_RESULTS

col = get_collection()

# (query, group) — group is "relevant" or "off-topic".
# Relevant queries are spread across all 8 ingested games.
QUERIES = [
    # --- relevant: real rules questions, one or more per game ---
    ("How many resource cards do I start with in Catan?", "relevant"),
    ("When can I build a settlement?", "relevant"),
    ("How do I make an accusation in Clue?", "relevant"),
    ("How does the spymaster give clues in Codenames?", "relevant"),
    ("What happens when I land on Go in Monopoly?", "relevant"),
    ("How do you build hotels in Monopoly?", "relevant"),
    ("How does an outbreak spread in Pandemic?", "relevant"),
    ("How do I attack a territory in Risk?", "relevant"),
    ("How do I claim a route in Ticket to Ride?", "relevant"),
    ("What does a wild card do in Uno?", "relevant"),
    # --- off-topic: nothing in any rulebook should match these well ---
    ("What is the weather forecast for tomorrow?", "off-topic"),
    ("How do I file my income taxes?", "off-topic"),
    ("What is the capital of France?", "off-topic"),
    ("What's a good recipe for chocolate chip cookies?", "off-topic"),
    ("How do I reset my email password?", "off-topic"),
    # Adversarial: brush against game vocab (cards/dice/money/board/win) but
    # have no answer in any rulebook — these stress the off-topic floor hardest.
    ("How do credit cards calculate interest?", "off-topic"),
    ("What casino dice games have the best odds?", "off-topic"),
    ("How do I win an argument with my boss?", "off-topic"),
    ("How much money should I keep in my savings account?", "off-topic"),
]


def top_distances(query, k=N_RESULTS):
    """Return the list of top-k cosine distances for a single query."""
    result = col.query(
        query_texts=[query],
        n_results=k,
        include=["distances"],
    )
    return result["distances"][0]  # [0]: unwrap the single-query outer list


def avg(values):
    return sum(values) / len(values) if values else float("nan")


def best_mid_worst(distances):
    """Return (best, mid, worst) for a result list of any length k.

    best  = first (lowest distance), mid = median position, worst = last.
    Every index is derived from the actual length and only after confirming
    the list is non-empty, so all three accesses are guaranteed in-bounds for
    any k >= 1. Returns (None, None, None) for an empty list.
    """
    n = len(distances)
    if n == 0:
        return None, None, None
    return distances[0], distances[n // 2], distances[-1]


def collect_positions(rows):
    """rows: list of (query, distances). Return (bests, mids, worsts) lists,
    skipping any row that returned no results."""
    triples = [best_mid_worst(d) for _, d in rows]
    bests = [b for b, _, _ in triples if b is not None]
    mids = [m for _, m, _ in triples if m is not None]
    worsts = [w for _, _, w in triples if w is not None]
    return bests, mids, worsts


def summarize(label, rows):
    """rows: list of (query, distances). Prints avg best/mid/worst across rows."""
    bests, mids, worsts = collect_positions(rows)
    print(
        f"{label:<22} avg best: {avg(bests):.3f} | "
        f"avg mid: {avg(mids):.3f} | avg worst: {avg(worsts):.3f}"
    )
    return bests, worsts


def main():
    n = col.count()
    print(f"{n} chunks in collection.\n")
    if n == 0:
        print("Collection is empty — run ingestion before calibrating.")
        return
    if n < N_RESULTS:
        print(
            f"Warning: only {n} chunks stored; queries will return < {N_RESULTS} results.\n"
        )

    relevant_rows = []
    offtopic_rows = []

    # Per-query detail table.
    for query, group in QUERIES:
        dists = top_distances(query)
        cols = "  ".join(f"{d:.3f}" for d in dists)
        print(f"[{group:<9}] {cols:<22}  {query}")
        (relevant_rows if group == "relevant" else offtopic_rows).append((query, dists))

    # Grouped + overall summary.
    print("\n── Summary ──")
    _, rel_worsts = summarize("Relevant queries", relevant_rows)
    off_bests, _ = summarize("Off-topic queries", offtopic_rows)

    all_rows = relevant_rows + offtopic_rows
    all_bests, all_mids, all_worsts = collect_positions(all_rows)
    print(
        f"{'Overall':<22} avg best: {avg(all_bests):.3f} | "
        f"avg mid: {avg(all_mids):.3f} | avg worst: {avg(all_worsts):.3f}"
    )

    # The decision-useful number: gap between worst relevant and best off-topic.
    if rel_worsts and off_bests:
        worst_relevant = max(rel_worsts)
        best_offtopic = min(off_bests)
        print("\n── Threshold band ──")
        print(f"Worst relevant top-3 distance : {worst_relevant:.3f}")
        print(f"Best off-topic distance       : {best_offtopic:.3f}")
        if worst_relevant < best_offtopic:
            print(
                f"Clean gap — pick a threshold between {worst_relevant:.3f} "
                f"and {best_offtopic:.3f}."
            )
        else:
            print(
                "Overlap — relevant and off-topic distances mix; no single "
                "threshold cleanly separates them. Lean permissive and rely on "
                "the LLM's escape hatch."
            )


if __name__ == "__main__":
    main()
