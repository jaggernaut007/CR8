import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders, setMockAuth, resetMockAuth, getMockAuth } from "@/test/test-utils";
import LoginPage from "./LoginPage";

const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return { ...actual, useNavigate: () => mockNavigate };
});

beforeEach(() => {
  resetMockAuth();
  vi.clearAllMocks();
});

describe("LoginPage", () => {
  it("renders sign in form by default", () => {
    renderWithProviders(<LoginPage />);
    expect(screen.getByRole("heading", { name: "Sign In" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("toggles to register mode", () => {
    renderWithProviders(<LoginPage />);
    fireEvent.click(screen.getByText("Create Account"));
    expect(screen.getByText("Display Name")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Create Account" })).toBeInTheDocument();
  });

  it("calls login on sign in submit", async () => {
    getMockAuth().login.mockResolvedValue(undefined);
    renderWithProviders(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(getMockAuth().login).toHaveBeenCalledWith("test@example.com", "password123");
    });
  });

  it("navigates to dashboard after successful login", async () => {
    getMockAuth().login.mockResolvedValue(undefined);
    renderWithProviders(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("calls register on create account submit", async () => {
    getMockAuth().register.mockResolvedValue(undefined);
    renderWithProviders(<LoginPage />);

    fireEvent.click(screen.getByText("Create Account"));
    fireEvent.change(screen.getByLabelText("Display Name"), { target: { value: "Test User" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(getMockAuth().register).toHaveBeenCalledWith("test@example.com", "password123", "Test User");
    });
  });

  it("displays error when present", () => {
    setMockAuth({ error: "Invalid credentials" });
    renderWithProviders(<LoginPage />);
    expect(screen.getByTestId("auth-error")).toHaveTextContent("Invalid credentials");
  });

  it("shows loading state", () => {
    setMockAuth({ isLoading: true });
    renderWithProviders(<LoginPage />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders how it works section", () => {
    renderWithProviders(<LoginPage />);
    expect(screen.getByText("How it works")).toBeInTheDocument();
    expect(screen.getByText("Upload")).toBeInTheDocument();
    expect(screen.getByText("Generate")).toBeInTheDocument();
    expect(screen.getByText("Learn")).toBeInTheDocument();
  });

  it("clears error when toggling mode", () => {
    setMockAuth({ error: "Some error" });
    renderWithProviders(<LoginPage />);
    fireEvent.click(screen.getByText("Create Account"));
    expect(getMockAuth().clearError).toHaveBeenCalled();
  });
});
