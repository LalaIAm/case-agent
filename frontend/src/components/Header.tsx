/**
 * App header with navigation, title, user email, and logout.
 */
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Button } from './Button';

export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/' || location.pathname === '/dashboard';
    return location.pathname.startsWith(path);
  };

  return (
    <header className="border-b border-gray-200 bg-white px-6 py-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link
            to="/"
            className="text-xl font-semibold text-blue-900 hover:text-blue-700"
          >
            Minnesota Conciliation Court Case Agent
          </Link>
          {user && (
            <nav className="flex gap-4" aria-label="Main navigation">
              <Link
                to="/"
                className={`text-sm font-medium ${
                  isActive('/') && !isActive('/cases')
                    ? 'text-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Dashboard
              </Link>
              <Link
                to="/intake"
                className={`text-sm font-medium ${
                  isActive('/intake') ? 'text-blue-600' : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                New Case
              </Link>
            </nav>
          )}
        </div>
        {user && (
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{user.email}</span>
            <Button type="button" variant="secondary" onClick={handleLogout}>
              Log out
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
