# Streamlit multipage apps have no enforced entry point

*From LEARNINGS.md, section "From the original (pre-rewrite) codebase".*

**Streamlit multipage apps have no enforced entry point** — users can navigate directly to `pages/X.py`. The original handles this by checking `'df' in st.session_state` and erroring out. Worth designing around in the rewrite.
