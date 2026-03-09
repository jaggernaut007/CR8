import { type ReactNode } from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { BrowserRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const defaultMockAuth = {
  user: null as { id: string; email: string; display_name: string | null; role: string } | null,
  isLoading: false,
  error: null as string | null,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  clearError: vi.fn(),
};

let _mockAuthOverrides: Partial<typeof defaultMockAuth> = {};

export function setMockAuth(overrides: Partial<typeof defaultMockAuth>) {
  _mockAuthOverrides = { ..._mockAuthOverrides, ...overrides };
}

export function resetMockAuth() {
  _mockAuthOverrides = {};
  defaultMockAuth.login = vi.fn();
  defaultMockAuth.register = vi.fn();
  defaultMockAuth.logout = vi.fn();
  defaultMockAuth.clearError = vi.fn();
}

/** Returns the current merged mock auth state. Use for assertions on mock fns. */
export function getMockAuth() {
  return { ...defaultMockAuth, ..._mockAuthOverrides };
}

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ ...defaultMockAuth, ..._mockAuthOverrides }),
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

export function renderWithProviders(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  const queryClient = createTestQueryClient();

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  }

  return { ...render(ui, { wrapper: Wrapper, ...options }), queryClient };
}
