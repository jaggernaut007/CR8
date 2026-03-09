import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/test/test-utils";
import ScoreSummary from "./ScoreSummary";

describe("ScoreSummary", () => {
  it("shows percentage", () => {
    renderWithProviders(<ScoreSummary score={8} total={10} percentage={80} />);
    expect(screen.getByText("80%")).toBeInTheDocument();
  });

  it("shows score fraction", () => {
    renderWithProviders(<ScoreSummary score={8} total={10} percentage={80} />);
    expect(screen.getByTestId("score-fraction")).toHaveTextContent("8 / 10 correct");
  });

  it("shows Excellent for >= 80%", () => {
    renderWithProviders(<ScoreSummary score={8} total={10} percentage={80} />);
    expect(screen.getByTestId("score-label")).toHaveTextContent("Excellent");
  });

  it("shows Good for >= 60%", () => {
    renderWithProviders(<ScoreSummary score={6} total={10} percentage={60} />);
    expect(screen.getByTestId("score-label")).toHaveTextContent("Good");
  });

  it("shows Needs improvement for < 60%", () => {
    renderWithProviders(<ScoreSummary score={3} total={10} percentage={30} />);
    expect(screen.getByTestId("score-label")).toHaveTextContent("Needs improvement");
  });
});
