import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { SessionPage } from './pages/SessionPage';
import { PocPage } from './pages/PocPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionPage />} />
        <Route path="/poc" element={<PocPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
