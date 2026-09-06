import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test/test-utils";
import ForgotPasswordPage from "./ForgotPasswordPage";

vi.mock("@/api/auth", () => ({
  requestPasswordReset: vi.fn(),
}));

import { requestPasswordReset } from "@/api/auth";
const mockRequest = vi.mocked(requestPasswordReset);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ForgotPasswordPage", () => {
  it("renders the form", () => {
    renderWithProviders(<ForgotPasswordPage />);
    expect(
      screen.getByRole("heading", { name: "Forgot Password" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });

  it("submits the email and shows a success message", async () => {
    mockRequest.mockResolvedValue({
      message: "If that email exists, a reset link has been sent.",
    });
    renderWithProviders(<ForgotPasswordPage />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith("test@example.com");
    });
    await waitFor(() => {
      expect(screen.getByTestId("forgot-success")).toBeInTheDocument();
    });
  });

  it("shows an error message when the request fails", async () => {
    mockRequest.mockRejectedValue({ body: { error: "Too many requests" } });
    renderWithProviders(<ForgotPasswordPage />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(screen.getByTestId("auth-error")).toHaveTextContent(
        "Too many requests",
      );
    });
  });
});
