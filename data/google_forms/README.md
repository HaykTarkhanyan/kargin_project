# data/google_forms/

Local copies of four public Google Forms quizzes about Kargin sketches, fetched 2026-09-11 with the Playwright MCP.

| Folder | Title | Questions | URL |
|---|---|---|---|
| `1/` | Կարգին հաղորդում | 15 | https://docs.google.com/forms/d/e/1FAIpQLSd99rjjFwKas8vIiVTdfkXuIYJblKN2qct-e05BztBMiT9M5Q/viewform |
| `2/` | Կարգին հաղորդում Vol. 2 | 16 | https://docs.google.com/forms/d/e/1FAIpQLSeXV2r44kmyRNtMkaBxshS86ZHSVP_9Hft_E26Pkug3-ZhnNg/viewform |
| `3/` | Կարգին հաղորդման թեստ 1 | 13 | https://docs.google.com/forms/d/e/1FAIpQLSfKV-wC1fh043B3UffO1qgLAITHXrRyutlrquZQMu7DIKtsHw/viewform |
| `4/` | Կարգին հաղորդում թեստ 2 | 13 | https://docs.google.com/forms/d/e/1FAIpQLSe_3NBgJwXichYb1b9dyyzye-8MWgcyJNKYTSCdVbYDlhM8aA/viewform |

Forms 1 and 2 are image quizzes (a still from a sketch plus four answer options per question; form 2 ends
with one image-option question and a free-text feedback field).
Forms 3 and 4 are named quizzes: a banner image, name + surname fields, then 10 numbered questions;
some questions there use image answer options instead of a question image.

`index.json` is the same table as machine-readable data.

## Files per folder

Raw capture (what the browser had, untouched apart from JSON-unwrapping):

- `form<n>_data.json` - page URL, title, fetch time, the page's `FB_PUBLIC_LOAD_DATA_` array (the full form
  definition Google ships to the browser), and the visible body text.
- `form<n>_page.html` - full rendered HTML of the viewform page.
- `form<n>.png` - full-page screenshot.

Derived by `scripts/non_essential/parse_google_forms.py` (re-run it to regenerate):

- `form.json` - structured questions: id, text, type, options, required flag, image metadata.
- `form.md` - the same as readable markdown with the images inlined.
- `page_text.txt` - the visible page text as rendered.
- `images/q<nn>.<ext>` - image attached to question nn; `images/q<nn>_opt<k>.<ext>` - image on answer option k.
  Extension follows the served content type (mostly png, some jpg). Downloaded at original resolution
  (the page itself shows downscaled copies).

## Limits

- Correct answers are NOT in the dump. Google withholds quiz grading from the public page until a
  response is submitted, so only questions and options are available.
- Per-question point values appear only in `page_text.txt` ("1 միավոր" lines), not in `form.json`.
