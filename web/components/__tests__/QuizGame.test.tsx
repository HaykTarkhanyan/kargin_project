import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import QuizGame from "@/components/QuizGame";

vi.mock("@/lib/quizzes", () => ({
  QUIZZES: [
    {
      id: "t1",
      level: 1,
      title: "Test",
      difficulty: "x",
      passPct: 0.5,
      questions: [
        {
          prompt: "Still question",
          image: "/quiz/still.jpg",
          options: ["a", "b", "c", "d"],
          correctIndex: 0,
          explanation: "because",
          sketchId: "vid123",
        },
        {
          prompt: "Picture question",
          options: ["1", "2", "3", "4"],
          optionImages: ["/quiz/p1.jpg", "/quiz/p2.jpg", "/quiz/p3.jpg", "/quiz/p4.jpg"],
          correctIndex: 1,
        },
      ],
    },
  ],
}));

describe("QuizGame with images", () => {
  beforeEach(() => localStorage.clear());

  it("shows the question still and one picture per option", () => {
    render(<QuizGame />);
    fireEvent.click(screen.getByText("Սկսել"));
    const srcs = screen.getAllByRole("presentation").map((img) => img.getAttribute("src"));
    expect(srcs).toEqual(["/quiz/still.jpg", "/quiz/p1.jpg", "/quiz/p2.jpg", "/quiz/p3.jpg", "/quiz/p4.jpg"]);
  });

  it("links to the sketch only after the answers are checked", () => {
    render(<QuizGame />);
    fireEvent.click(screen.getByText("Սկսել"));
    expect(screen.queryByText("Դիտել սքեթչը →")).toBeNull();
    fireEvent.click(screen.getByText("a"));
    fireEvent.click(screen.getByText("2"));
    fireEvent.click(screen.getByText("Ստուգել"));
    const link = screen.getByText("Դիտել սքեթչը →");
    expect(link.getAttribute("href")).toBe("/sketch/vid123");
    expect(screen.getByText(/because/)).toBeTruthy();
  });
});
