"""Turn the raw Google Forms dumps under data/google_forms/<n>/ into clean files.

Input per form folder (produced by a Playwright session, see data/google_forms/README.md):
  form<n>_data.json   url, title, fetchedAt, FB_PUBLIC_LOAD_DATA_ (fbPublicLoadData), bodyText
  form<n>_page.html   full rendered HTML of the viewform page
  form<n>.png         full-page screenshot

Output per form folder:
  form.json           structured questions/options parsed from FB_PUBLIC_LOAD_DATA_
  form.md             human-readable rendering of the same
  page_text.txt       the page's visible text as rendered
  images/q<nn>.jpg    the image attached to each question, downloaded at full size

Usage:
  uv run python scripts/non_essential/parse_google_forms.py
"""

import json
import logging
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
FORMS_DIR = ROOT / "data" / "google_forms"

# Item type codes used inside FB_PUBLIC_LOAD_DATA_.
TYPE_NAMES = {
    0: "short_answer",
    1: "paragraph",
    2: "multiple_choice",
    3: "dropdown",
    4: "checkboxes",
    5: "linear_scale",
    6: "title_and_description",
    7: "grid",
    8: "section",
    9: "date",
    10: "time",
    11: "image",
    12: "video",
    13: "file_upload",
}

# The page embeds a "=w<width>" suffix that returns a downscaled copy; the bare token returns the original.
IMG_RE = re.compile(r'<img[^>]*?src="(https://docs\.google\.com/forms-images-rt/[A-Za-z0-9_-]+)(?:=w\d+)?"')


def setup_logging() -> logging.Logger:
    Path(ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs" / "parse_google_forms.log", encoding="utf-8"),
        ],
    )
    return logging.getLogger(__name__)


log = setup_logging()


def load_raw(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_image(img: list) -> dict:
    return {"id": img[0], "width": img[2][0], "height": img[2][1]}


def parse_item(item: list) -> dict:
    qtype = item[3]
    entries = []
    for e in item[4] or []:
        options = []
        for o in e[1] or []:
            # An option can carry its own image at index 5 (image-choice questions); unlike the
            # question header image it is not wrapped in an outer list.
            opt_img = parse_image(o[5]) if len(o) > 5 and o[5] else None
            options.append({"text": o[0], "image": opt_img})
        entries.append({"entry_id": e[0], "options": options, "required": bool(e[2])})
    if qtype == 11:
        # A standalone image item keeps its image at index 6, unwrapped.
        image = parse_image(item[6]) if len(item) > 6 and item[6] else None
    else:
        image = parse_image(item[9][0]) if len(item) > 9 and item[9] else None
    return {
        "item_id": item[0],
        "question": item[1],
        "help_text": item[2],
        "type_code": qtype,
        "type": TYPE_NAMES.get(qtype, f"unknown_{qtype}"),
        "entries": entries,
        "image": image,
    }


def parse_form(raw: dict) -> dict:
    fb = raw["fbPublicLoadData"]
    items = [parse_item(it) for it in fb[1][1]]
    description_html = fb[1][24][1] if len(fb[1]) > 24 and fb[1][24] else None
    return {
        "url": raw["url"],
        "fetched_at": raw["fetchedAt"],
        "title": raw["title"],
        # fb[3] is the Drive document name, which can lag behind the displayed title ("Blank Quiz").
        "internal_name": fb[3],
        "description": fb[1][0],
        "description_html": description_html,
        "question_count": len(items),
        "questions": items,
    }


def image_slots(form: dict):
    """Yield (image dict, file stem) in the order the page renders them: question header, then its options."""
    for i, q in enumerate(form["questions"], start=1):
        if q["image"]:
            yield q["image"], f"q{i:02d}"
        for e in q["entries"]:
            for j, opt in enumerate(e["options"], start=1):
                if opt["image"]:
                    yield opt["image"], f"q{i:02d}_opt{j}"


def attach_images(form: dict, html: str) -> None:
    """Pair image URLs (DOM order) with the images the form data declares (form order)."""
    urls = IMG_RE.findall(html)
    slots = list(image_slots(form))
    if len(urls) != len(slots):
        raise RuntimeError(
            f"{form['title']}: {len(urls)} image URLs in HTML but form data declares {len(slots)} images"
        )
    for (img, _stem), url in zip(slots, urls):
        img["url"] = url


EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}


def download_images(form: dict, out_dir: Path) -> None:
    """Download each image once, naming the file by its real content type, and record the path."""
    out_dir.mkdir(exist_ok=True)
    for img, stem in image_slots(form):
        existing = sorted(out_dir.glob(f"{stem}.*"))
        if existing:
            img["file"] = f"images/{existing[0].name}"
            continue
        r = requests.get(img["url"], timeout=60)
        r.raise_for_status()
        ctype = r.headers.get("content-type", "").split(";")[0].strip()
        if ctype not in EXTENSIONS:
            raise RuntimeError(f"{stem}: expected an image, got content-type {ctype!r}")
        dest = out_dir / f"{stem}{EXTENSIONS[ctype]}"
        dest.write_bytes(r.content)
        img["file"] = f"images/{dest.name}"
        log.info(f"downloaded {dest.relative_to(ROOT)} ({len(r.content)} bytes, {ctype})")


def render_markdown(form: dict) -> str:
    lines = [f"# {form['title']}", "", f"Source: {form['url']}", f"Fetched: {form['fetched_at']}", ""]
    if form["description"]:
        lines += ["## Description", "", form["description"].strip(), ""]
    lines += [f"## Questions ({form['question_count']})", ""]
    for i, q in enumerate(form["questions"], start=1):
        lines.append(f"### {i}. {q['question'] or '(no text)'}")
        lines.append("")
        meta = [f"type: {q['type']}"]
        if any(e["required"] for e in q["entries"]):
            meta.append("required")
        lines.append(f"_{', '.join(meta)}_")
        lines.append("")
        if q["help_text"]:
            lines += [q["help_text"], ""]
        if q["image"]:
            lines += [f"![question image]({q['image']['file']})", ""]
        for e in q["entries"]:
            for opt in e["options"]:
                line = f"- {opt['text']}"
                if opt["image"]:
                    line += f" ![option image]({opt['image']['file']})"
                lines.append(line)
        lines.append("")
    return "\n".join(lines)


def process(form_dir: Path) -> dict:
    n = form_dir.name
    raw = load_raw(form_dir / f"form{n}_data.json")
    html = (form_dir / f"form{n}_page.html").read_text(encoding="utf-8")
    form = parse_form(raw)
    attach_images(form, html)
    download_images(form, form_dir / "images")
    (form_dir / "form.json").write_text(json.dumps(form, ensure_ascii=False, indent=2), encoding="utf-8")
    (form_dir / "form.md").write_text(render_markdown(form), encoding="utf-8")
    (form_dir / "page_text.txt").write_text(raw["bodyText"], encoding="utf-8")
    log.info(f"form {n}: '{form['title']}' -> {form['question_count']} questions")
    return form


def main() -> None:
    form_dirs = sorted(p for p in FORMS_DIR.iterdir() if p.is_dir() and p.name.isdigit())
    if not form_dirs:
        raise RuntimeError(f"no numbered form folders under {FORMS_DIR}")
    summary = []
    for d in form_dirs:
        form = process(d)
        summary.append(
            {
                "folder": d.name,
                "title": form["title"],
                "url": form["url"],
                "question_count": form["question_count"],
                "fetched_at": form["fetched_at"],
            }
        )
    (FORMS_DIR / "index.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"wrote {FORMS_DIR / 'index.json'} with {len(summary)} forms")


if __name__ == "__main__":
    main()
