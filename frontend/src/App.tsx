import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AuthPage } from './pages/AuthPage';
import { IntakePage } from './pages/IntakePage';
import { CaseDashboard } from './pages/CaseDashboard';
import { CaseDetail } from './pages/CaseDetail';

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<AuthPage />} />
              <Route path="/register" element={<AuthPage />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <CaseDashboard />
                  </ProtectedRoute>
                }
              />
              <Route path="/dashboard" element={<Navigate to="/" replace />} />
              <Route
                path="/intake"
                element={
                  <ProtectedRoute>
                    <IntakePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/cases/:caseId"
                element={
                  <ProtectedRoute>
                    <ErrorBoundary>
                      <CaseDetail />
                    </ErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
