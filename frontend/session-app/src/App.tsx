import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { SessionPage } from './pages/SessionPage';
import { PocPage } from './pages/PocPage';
import { PocSatominPage } from './pages/PocSatominPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionPage />} />
        <Route path="/poc" element={<PocPage />} />
        <Route path="/poc_satomin" element={<PocSatominPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
