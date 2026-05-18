import { NavLink, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      <header className="border-b border-zinc-200 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-8">
          <NavLink
            to="/"
            className="text-lg font-semibold tracking-tight"
          >
            interp-eval
          </NavLink>
          <nav className="flex items-center gap-6 text-sm">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                isActive
                  ? "text-zinc-900 font-medium"
                  : "text-zinc-500 hover:text-zinc-900"
              }
            >
              runs
            </NavLink>
            <NavLink
              to="/compare"
              className={({ isActive }) =>
                isActive
                  ? "text-zinc-900 font-medium"
                  : "text-zinc-500 hover:text-zinc-900"
              }
            >
              compare
            </NavLink>
          </nav>
          <div className="ml-auto text-xs text-zinc-400">
            three-scorer LLM evaluation
          </div>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}