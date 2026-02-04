/**
 * App header with title, user email, and logout.
 */
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Button } from './Button';

export function Header() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  return (
    <header className="border-b border-gray-200 bg-white px-6 py-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-blue-900">
          Minnesota Conciliation Court Case Agent
        </h1>
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
