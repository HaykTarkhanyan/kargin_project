# A server-rendered element passed as a prop into a client component keeps its data off the client, but does not reach the static HTML

*From LEARNINGS.md, section "2026-09-12 — collections, and four things that looked like bugs but were not".*

**A server-rendered element passed as a prop into a client component keeps its data off the client, but does not reach the static HTML.** `<SearchExperience strip={<CollectionStrip />} />` means `collections.json` never ships to the browser. It still renders only after hydration, because `SearchExperience` wraps its body in a Suspense boundary and the body reads search params, so the export emits the fallback — which is why the live home page's HTML is a 10.5 KB shell with no cards in it. Fine here (everything below the header behaves that way already), but it means the home strip is not crawlable and `/collections` is the page that carries this content for search engines.
