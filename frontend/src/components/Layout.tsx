import { NavLink, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="lab-shell">
      <aside className="lab-sidebar">
        <NavLink to="/" className="lab-brand"><span className="brand-mark">ie.</span><span>interp-eval<small>Behavioral evaluation lab</small></span></NavLink>
        <p className="rail-label">WORKSPACE</p>
        <nav aria-label="Main navigation">
          <NavLink to="/" end><span>01</span> Experiments</NavLink>
          <NavLink to="/compare"><span>02</span> Compare prompts</NavLink>
        </nav>
        <div className="rail-notes"><p className="rail-label">READING THE RESULTS</p><p>Rules check expected behavior. A judge rates the review. Probes add another signal to investigate.</p><p>A disagreement is a reason to inspect a case—not proof that any scorer is right.</p></div>
        <a className="source-link" href="https://github.com/aayushhks/llm-eval-with-probes" target="_blank" rel="noreferrer">Source & methodology ↗</a>
      </aside>
      <div className="lab-content"><header className="lab-topbar"><span>RESEARCH WORKSPACE / CODE REVIEW</span><span className="archive-label">Recorded experiments</span></header><main><Outlet /></main><footer>Aayush Kumar <span>Python · FastAPI · PostgreSQL · React · scikit-learn</span></footer></div>
    </div>
  );
}
