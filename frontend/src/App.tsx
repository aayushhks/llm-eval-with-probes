import { useEffect, useState } from "react";

export default function App() {
  const [health, setHealth] = useState<string>("checking...");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setHealth(d.status))
      .catch(() => setHealth("unreachable"));
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-semibold tracking-tight">interp-eval</h1>
        <p className="mt-2 text-zinc-400">Backend health: <span className="font-mono">{health}</span></p>
      </div>
    </div>
  );
}
