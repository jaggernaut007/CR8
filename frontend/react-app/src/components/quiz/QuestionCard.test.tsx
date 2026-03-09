import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/test/test-utils";
import QuestionCard from "./QuestionCard";

const baseQuestion = {
  id: "q1",
  question_text: "What is 2 + 2?",
  options: ["3", "4", "5", "6"],
  difficulty: "easy",
};

describe("QuestionCard", () => {
  it("renders question text", () => {
    renderWithProviders(
      <QuestionCard question={baseQuestion} questionNumber={1} selectedIndex={undefined} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument();
  });

  it("renders all four options", () => {
    renderWithProviders(
      <QuestionCard question={baseQuestion} questionNumber={1} selectedIndex={undefined} onSelect={vi.fn()} />,
    );
    expect(screen.getByText(/^3$/)).toBeInTheDocument();
    expect(screen.getByText(/^4$/)).toBeInTheDocument();
    expect(screen.getByText(/^5$/)).toBeInTheDocument();
    expect(screen.getByText(/^6$/)).toBeInTheDocument();
  });

  it("shows question number", () => {
    renderWithProviders(
      <QuestionCard question={baseQuestion} questionNumber={5} selectedIndex={undefined} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("Question 5")).toBeInTheDocument();
  });

  it("highlights selected option via aria-pressed", () => {
    renderWithProviders(
      <QuestionCard question={baseQuestion} questionNumber={1} selectedIndex={1} onSelect={vi.fn()} />,
    );
    const option = screen.getByTestId("option-1");
    expect(option).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onSelect when clicking an option", () => {
    const onSelect = vi.fn();
    renderWithProviders(
      <QuestionCard question={baseQuestion} questionNumber={1} selectedIndex={undefined} onSelect={onSelect} />,
    );
    fireEvent.click(screen.getByTestId("option-2"));
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("shows difficulty badge", () => {
    renderWithProviders(
      <QuestionCard question={baseQuestion} questionNumber={1} selectedIndex={undefined} onSelect={vi.fn()} />,
    );
    expect(screen.getByTestId("difficulty-badge")).toHaveTextContent("easy");
  });

  it("does not show difficulty badge when absent", () => {
    const q = { ...baseQuestion, difficulty: undefined };
    renderWithProviders(
      <QuestionCard question={q} questionNumber={1} selectedIndex={undefined} onSelect={vi.fn()} />,
    );
    expect(screen.queryByTestId("difficulty-badge")).not.toBeInTheDocument();
  });

  it("shows feedback in review mode", () => {
    renderWithProviders(
      <QuestionCard
        question={baseQuestion}
        questionNumber={1}
        selectedIndex={1}
        onSelect={vi.fn()}
        showResult
        correctIndex={1}
        feedback="Correct! 2+2=4"
      />,
    );
    expect(screen.getByTestId("feedback")).toHaveTextContent("Correct! 2+2=4");
  });

  it("disables clicks when disabled", () => {
    const onSelect = vi.fn();
    renderWithProviders(
      <QuestionCard question={baseQuestion} questionNumber={1} selectedIndex={undefined} onSelect={onSelect} disabled />,
    );
    fireEvent.click(screen.getByTestId("option-0"));
    expect(onSelect).not.toHaveBeenCalled();
  });
});
