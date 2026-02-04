/**
 * Placeholder dashboard for authenticated users.
 */
import { Header } from '../components/Header';

export function Dashboard() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <Header />
      <main className="p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-2">Welcome to Case Agent</h2>
        <p className="text-gray-600">Full dashboard coming in Phase 11.</p>
      </main>
    </div>
  );
}
