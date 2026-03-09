/**
 * App root — sets up routing, auth context, and Tanstack Query provider.
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Navbar from "@/components/Navbar";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import UploadPage from "@/pages/UploadPage";
import ProgressPage from "@/pages/ProgressPage";
import ResultsPage from "@/pages/ResultsPage";
import QuizPage from "@/pages/QuizPage";
import QuizResultsPage from "@/pages/QuizResultsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Navbar />
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/progress/:jobId" element={<ProgressPage />} />
              <Route path="/results/:jobId" element={<ResultsPage />} />
              <Route path="/quiz/:quizId" element={<QuizPage />} />
              <Route path="/quiz/:quizId/results" element={<QuizResultsPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
