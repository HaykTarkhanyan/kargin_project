import { describe, it, expect } from "vitest";
import { toFields, MESSAGE_MAX, CONTACT_MAX } from "@/lib/feedback";

const base = { kind: "missing" as const, message: "  կովի սքեթչը  " };

describe("feedback encoding", () => {
  it("encodes the required fields and trims the message", () => {
    const f = toFields(base, "sess", "agent");
    expect(f.kind).toEqual({ stringValue: "missing" });
    expect(f.message).toEqual({ stringValue: "կովի սքեթչը" });
    expect(f.sessionId).toEqual({ stringValue: "sess" });
    expect(f.ua).toEqual({ stringValue: "agent" });
  });

  it("omits optional fields rather than sending empty strings", () => {
    // The rules allow them absent but require a string when present; sending ""
    // would store noise a human then has to read past.
    const f = toFields({ ...base, query: "", contact: "", sketchId: "" }, "s", "u");
    expect("query" in f).toBe(false);
    expect("contact" in f).toBe(false);
    expect("sketchId" in f).toBe(false);
  });

  it("includes optional fields when they carry something", () => {
    const f = toFields({ ...base, query: "կով", sketchId: "abc", contact: "@hayk", source: "watch" }, "s", "u");
    expect(f.query).toEqual({ stringValue: "կով" });
    expect(f.sketchId).toEqual({ stringValue: "abc" });
    expect(f.contact).toEqual({ stringValue: "@hayk" });
    expect(f.source).toEqual({ stringValue: "watch" });
  });

  // The clamps here and the caps in firestore.rules have to agree: anything
  // longer is rejected wholesale, losing the report instead of trimming it.
  it("clamps to the limits the rules enforce", () => {
    const f = toFields(
      { ...base, message: "x".repeat(MESSAGE_MAX + 50), contact: "y".repeat(CONTACT_MAX + 50) },
      "s".repeat(100),
      "u".repeat(400),
    );
    expect(f.message.stringValue.length).toBe(MESSAGE_MAX);
    expect(f.contact.stringValue.length).toBe(CONTACT_MAX);
    expect(f.sessionId.stringValue.length).toBe(64);
    expect(f.ua.stringValue.length).toBe(256);
  });
});
