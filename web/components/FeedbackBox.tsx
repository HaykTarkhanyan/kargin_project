"use client";
import { useRef, useState } from "react";
import { CONTACT_MAX, MESSAGE_MAX, submitFeedback, type FeedbackKind } from "@/lib/feedback";

type State = "closed" | "open" | "sending" | "sent" | "failed";

/**
 * "Couldn't find it? Tell us." — a report of a missing sketch or a mistake.
 *
 * Collapsed to a single line until asked for, because it sits under results a
 * visitor is still reading. It only becomes a form on a deliberate tap, and it
 * stays open with the text intact if sending fails, so nobody loses what they
 * wrote.
 */
export default function FeedbackBox({
  kind, query, sketchId, source, label, prompt,
}: {
  kind: FeedbackKind;
  query?: string;
  sketchId?: string;
  source: string;
  /** The button's own text. It has to say what it is with nothing around it. */
  label: string;
  /** Optional sentence above the button, where there is room to explain. */
  prompt?: string;
}) {
  const [state, setState] = useState<State>("closed");
  const [message, setMessage] = useState("");
  const [contact, setContact] = useState("");
  const [error, setError] = useState("");
  const field = useRef<HTMLTextAreaElement>(null);

  const open = () => {
    setState("open");
    // Focus after paint, so the field is actually there to receive it.
    requestAnimationFrame(() => field.current?.focus());
  };

  const send = async () => {
    if (!message.trim()) { field.current?.focus(); return; }
    setState("sending");
    setError("");
    try {
      await submitFeedback({ kind, message, query, sketchId, contact, source });
      setState("sent");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setState("failed");
    }
  };

  if (state === "sent") {
    return (
      <div className="k-border w-full rounded-lg border-kblue bg-surface px-4 py-3 text-sm font-semibold">
        ✓ Ստացանք, շնորհակալությո՛ւն։ {contact.trim() ? "Կպատասխանենք։" : "Կնայենք։"}
      </div>
    );
  }

  if (state === "closed") {
    // A bordered button, not a text link: as a link at the foot of the page this
    // was invisible on a phone — roughly thirty screens below the search box.
    return (
      <div>
        {prompt && <p className="mb-2 text-sm text-muted">{prompt}</p>}
        <button onClick={open}
          className="inline-flex min-h-11 items-center gap-2 rounded-full border-2 border-ink bg-surface px-4 py-2 text-xs font-bold hover:bg-ink hover:text-paper">
          ✍️ {label}
        </button>
      </div>
    );
  }

  const busy = state === "sending";
  return (
    // w-full so that opening it inside a row of pills takes the whole line
    // rather than being squeezed into what the collapsed button occupied.
    <div className="k-border k-shadow w-full rounded-lg bg-surface p-4">
      <div className="mb-2 font-display text-base tracking-wide">
        {kind === "missing" ? "ՉԳՏԱ՞Ր" : "ՍԽԱ՞Լ ԿԱ"}
      </div>
      {query && (
        <p className="mb-2 text-xs text-muted">
          Որոնումդ՝ <span className="font-bold text-ink">«{query}»</span>
        </p>
      )}
      <textarea
        ref={field}
        value={message}
        onChange={(e) => setMessage(e.target.value.slice(0, MESSAGE_MAX))}
        rows={3}
        disabled={busy}
        placeholder={kind === "missing"
          ? "Ո՞ր սքեթչն ես փնտրում — ինչ են ասում, ով է խաղում, ինչ է կատարվում…"
          : "Ի՞նչն է սխալ այս սքեթչում…"}
        // 16px minimum, or iOS Safari zooms the page when the field takes focus.
        className="w-full resize-y rounded-md border-2 border-ink/30 bg-card px-3 py-2 text-[16px] leading-snug outline-none focus:border-ink"
      />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <input
          value={contact}
          onChange={(e) => setContact(e.target.value.slice(0, CONTACT_MAX))}
          disabled={busy}
          placeholder="Կապ (ըստ ցանկության)"
          className="min-h-11 flex-1 rounded-md border-2 border-ink/30 bg-card px-3 text-[16px] outline-none focus:border-ink"
        />
        <button onClick={send} disabled={busy}
          className="k-border min-h-11 rounded-lg bg-korange px-5 font-bold text-[#1A1410] disabled:opacity-60">
          {busy ? "Ուղարկվում է…" : "Ուղարկել"}
        </button>
        <button onClick={() => setState("closed")} disabled={busy}
          className="min-h-11 px-2 text-sm font-semibold text-muted hover:text-ink">
          Չեղարկել
        </button>
      </div>
      {state === "failed" && (
        // Said plainly, with the text still in the box — the alternative is a
        // visitor believing a report was filed when it was not.
        <p className="mt-2 text-sm font-semibold text-kred">
          Չստացվեց ուղարկել։ Փորձի՛ր նորից։ <span className="font-normal opacity-70">({error})</span>
        </p>
      )}
    </div>
  );
}
