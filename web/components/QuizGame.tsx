"use client";
import { useEffect, useState } from "react";
import { QUIZZES, type Quiz } from "@/lib/quizzes";

type Progress = Record<string, number>; // quizId -> best fraction (0..1)
const KEY = "kargin_quiz_progress";

function loadProgress(): Progress {
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; }
}
function saveProgress(p: Progress) {
  try { localStorage.setItem(KEY, JSON.stringify(p)); } catch { /* ignore */ }
}
function stars(pct: number): number {
  return pct >= 0.9 ? 3 : pct >= 0.8 ? 2 : pct >= 0.7 ? 1 : 0;
}

const LEVELS = [...QUIZZES].sort((a, b) => a.level - b.level);

export default function QuizGame() {
  const [progress, setProgress] = useState<Progress>({});
  const [active, setActive] = useState<Quiz | null>(null);
  useEffect(() => { setProgress(loadProgress()); }, []);

  const record = (id: string, pct: number) =>
    setProgress((p) => {
      const next = { ...p, [id]: Math.max(p[id] ?? 0, pct) };
      saveProgress(next);
      return next;
    });

  if (active) return <Runner quiz={active} onDone={(pct) => record(active.id, pct)} onBack={() => setActive(null)} />;

  const passed = (q: Quiz) => (progress[q.id] ?? 0) >= q.passPct;
  const unlocked = (i: number) => i === 0 || passed(LEVELS[i - 1]);
  const passedCount = LEVELS.filter(passed).length;

  return (
    <main className="mx-auto max-w-2xl px-4 py-8 sm:px-7">
      <h1 className="font-display text-4xl sm:text-5xl">Քուիզ</h1>
      <p className="mt-2 text-muted">Անցի՛ր մակարդակները հերթով — յուրաքանչյուրը բացում է հաջորդը։</p>

      <div className="mt-4 h-3 overflow-hidden rounded-full border-2 border-ink bg-white">
        <div className="h-full bg-korange transition-all" style={{ width: `${(passedCount / LEVELS.length) * 100}%` }} />
      </div>
      <p className="mt-1 text-sm font-bold">{passedCount}/{LEVELS.length} մակարդակ անցած</p>

      <div className="mt-6 space-y-4">
        {LEVELS.map((q, i) => {
          const open = unlocked(i);
          const best = progress[q.id] ?? 0;
          const done = passed(q);
          return (
            <div key={q.id} className={`k-border rounded-xl p-4 ${open ? "k-shadow bg-card" : "bg-paper2 opacity-60"}`}>
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-kblue px-2.5 py-0.5 text-xs font-bold text-white">Մակարդակ {q.level}</span>
                    <span className="text-xs font-bold text-muted">{q.difficulty}</span>
                  </div>
                  <div className="mt-1.5 font-bold">{q.title}</div>
                  <div className="text-xs text-muted">
                    {q.questions.length} հարց{done ? ` · լավագույնը ${Math.round(best * 100)}%` : ""}
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  {done && <div className="text-lg leading-none">{"⭐".repeat(stars(best))}</div>}
                  {open ? (
                    <button onClick={() => setActive(q)} className="mt-1 k-border rounded-lg bg-korange px-4 py-2 text-sm font-bold">
                      {done ? "Կրկնել" : "Սկսել"}
                    </button>
                  ) : (
                    <div className="text-2xl">🔒</div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {passedCount === LEVELS.length && (
        <div className="mt-6 rounded-xl bg-ink p-5 text-center text-paper">
          <div className="text-3xl">🏆</div>
          <div className="mt-1 font-bold">Շնորհավո՛ր, անցար բոլոր մակարդակները։</div>
        </div>
      )}
    </main>
  );
}

function Runner({ quiz, onDone, onBack }: { quiz: Quiz; onDone: (pct: number) => void; onBack: () => void }) {
  const [answers, setAnswers] = useState<(number | null)[]>(Array(quiz.questions.length).fill(null));
  const [submitted, setSubmitted] = useState(false);

  const correct = answers.filter((a, i) => a === quiz.questions[i].correctIndex).length;
  const pct = correct / quiz.questions.length;
  const didPass = pct >= quiz.passPct;

  const submit = () => { setSubmitted(true); onDone(pct); };
  const retry = () => { setAnswers(Array(quiz.questions.length).fill(null)); setSubmitted(false); };

  return (
    <main className="mx-auto max-w-2xl px-4 py-8 sm:px-7">
      <button onClick={onBack} className="text-sm font-bold text-muted hover:text-ink">← Մակարդակներ</button>
      <h1 className="mt-2 font-display text-3xl">{quiz.title}</h1>
      <p className="text-sm text-muted">{quiz.difficulty} · անցնելու համար՝ {Math.round(quiz.passPct * 100)}%</p>

      <div className="mt-5 space-y-5">
        {quiz.questions.map((qq, qi) => (
          <div key={qi} className="k-border k-shadow rounded-xl bg-card p-4">
            <div className="font-bold">{qi + 1}. {qq.prompt}</div>
            <div className="mt-3 space-y-2">
              {qq.options.map((opt, oi) => {
                const chosen = answers[qi] === oi;
                const isCorrect = oi === qq.correctIndex;
                const style = submitted && isCorrect ? { background: "#bbf7d0", borderColor: "#15803d" }
                  : submitted && chosen && !isCorrect ? { background: "#fecaca", borderColor: "#b91c1c" }
                  : undefined;
                return (
                  <button key={oi} disabled={submitted} style={style}
                    onClick={() => setAnswers((a) => a.map((x, i) => (i === qi ? oi : x)))}
                    className={`block w-full rounded-lg border-2 border-ink px-3 py-2 text-left text-sm font-semibold ${!submitted && chosen ? "bg-kblue text-white" : "bg-white"}`}>
                    {opt}
                    {submitted && isCorrect ? " ✓" : ""}
                    {submitted && chosen && !isCorrect ? " ✗" : ""}
                  </button>
                );
              })}
            </div>
            {submitted && qq.explanation && <div className="mt-2 text-xs text-muted">💡 {qq.explanation}</div>}
          </div>
        ))}
      </div>

      {!submitted ? (
        <button onClick={submit} disabled={answers.some((a) => a === null)}
          className="mt-6 k-border k-shadow rounded-lg bg-korange px-6 py-3 font-bold disabled:opacity-50">
          Ստուգել
        </button>
      ) : (
        <div className={`mt-6 rounded-xl p-5 text-center ${didPass ? "bg-ink text-paper" : "k-border bg-paper2"}`}>
          <div className="text-3xl">{didPass ? "🎉" : "💪"}</div>
          <div className="mt-1 text-xl font-bold">{correct}/{quiz.questions.length} · {Math.round(pct * 100)}%</div>
          <div className="mt-1 text-sm">{didPass ? "Անցար։ Հաջորդ մակարդակը բացված է։" : `Պետք է ${Math.round(quiz.passPct * 100)}%։ Փորձիր նորից։`}</div>
          <div className="mt-3 flex justify-center gap-2">
            <button onClick={retry} className="k-border rounded-lg bg-card px-4 py-2 text-sm font-bold">Կրկնել</button>
            <button onClick={onBack} className="k-border rounded-lg bg-korange px-4 py-2 text-sm font-bold">Մակարդակներ</button>
          </div>
        </div>
      )}
    </main>
  );
}
