import { Routes, Route } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import EcgLab from "./pages/EcgLab";
import XrayLab from "./pages/XrayLab";
import Validation from "./pages/Validation";
import History from "./pages/History";

export default function App() {
  return (
    <AppProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/ecg" element={<EcgLab />} />
          <Route path="/xray" element={<XrayLab />} />
          <Route path="/validation" element={<Validation />} />
          <Route path="/history" element={<History />} />
        </Route>
      </Routes>
    </AppProvider>
  );
}
