import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import RunsList from "./pages/RunsList";
import RunDetailPage from "./pages/RunDetail";
import Validation from "./pages/Validation";
import Compare from "./pages/Compare";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<RunsList />} />
          <Route path="/runs/:id" element={<RunDetailPage />} />
          <Route path="/validation" element={<Validation />} />
          <Route path="/compare" element={<Compare />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
