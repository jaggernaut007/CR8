import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test/test-utils";
import ResetPasswordPage from "./ResetPasswordPage";

vi.mock("@/api/auth", () => ({
  resetPassword: vi.fn(),
}));

import { resetPassword } from "@/api/auth";
const mockReset = vi.mocked(resetPassword);

vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useSearchParams: () => [new URLSearchParams({ token: "test-token" })],
  };
});

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ResetPasswordPage", () => {
  it("renders the form", () => {
    renderWithProviders(<ResetPasswordPage />);
    expect(
      screen.getByRole("heading", { name: "Reset Password" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("New Password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument();
  });

  it("resets the password and shows a success message", async () => {
    mockReset.mockResolvedValue({
      message: "Password has been reset. You can now sign in.",
    });
    renderWithProviders(<ResetPasswordPage />);

    fireEvent.change(screen.getByLabelText("New Password"), {
      target: { value: "newpassword" },
    });
    fireEvent.change(screen.getByLabelText("Confirm Password"), {
      target: { value: "newpassword" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reset password" }));

    await waitFor(() => {
      expect(mockReset).toHaveBeenCalledWith("test-token", "newpassword");
    });
    await waitFor(() => {
      expect(screen.getByTestId("reset-success")).toBeInTheDocument();
    });
  });

  it("shows an error when passwords do not match", async () => {
    renderWithProviders(<ResetPasswordPage />);

    fireEvent.change(screen.getByLabelText("New Password"), {
      target: { value: "newpassword" },
    });
    fireEvent.change(screen.getByLabelText("Confirm Password"), {
      target: { value: "different" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reset password" }));

    await waitFor(() => {
      expect(screen.getByTestId("auth-error")).toHaveTextContent(
        "Passwords do not match",
      );
    });
    expect(mockReset).not.toHaveBeenCalled();
  });

  it("shows an error from the API when reset fails", async () => {
    mockReset.mockRejectedValue({
      body: { error: "Invalid or expired reset token" },
    });
    renderWithProviders(<ResetPasswordPage />);

    fireEvent.change(screen.getByLabelText("New Password"), {
      target: { value: "newpassword" },
    });
    fireEvent.change(screen.getByLabelText("Confirm Password"), {
      target: { value: "newpassword" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reset password" }));

    await waitFor(() => {
      expect(screen.getByTestId("auth-error")).toHaveTextContent(
        "Invalid or expired reset token",
      );
    });
  });
});
