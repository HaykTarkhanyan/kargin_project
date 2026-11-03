# `client.models.embed_content(contents=[a, b, c])` returns ONE embedding, not three, on Vertex - no error, no warning

*From LEARNINGS.md, section "2026-09-07 - gemini-embedding-2 silently ignores batched inputs".*

**`client.models.embed_content(contents=[a, b, c])` returns ONE embedding, not three, on Vertex - no error, no warning.** Verified with batches of 2, 4 and 8: every call came back with `len(response.embeddings) == 1`. Naive batching would have produced 44 vectors for 702 documents and misaligned every vector against its `video_id`, poisoning the similarity matrix with no visible failure. Fix: one request per document, `--workers` for throughput, and assert `len(embeddings) == 1` and `len(values) == dim` on every call. Never trust an embedding API's batch semantics without counting the returned vectors.
