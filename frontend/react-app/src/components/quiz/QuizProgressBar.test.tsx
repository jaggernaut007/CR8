import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/test/test-utils";
import QuizProgressBar from "./QuizProgressBar";

describe("QuizProgressBar", () => {
  it("shows current and total question text", () => {
    renderWithProviders(<QuizProgressBar current={3} total={10} answered={2} />);
    expect(screen.getByText("Question 3 of 10")).toBeInTheDocument();
  });

  it("shows answered count", () => {
    renderWithProviders(<QuizProgressBar current={1} total={10} answered={5} />);
    expect(screen.getByTestId("answered-count")).toHaveTextContent("5 answered");
  });

  it("renders progressbar with correct aria values", () => {
    renderWithProviders(<QuizProgressBar current={1} total={20} answered={10} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "10");
    expect(bar).toHaveAttribute("aria-valuemax", "20");
  });
});
