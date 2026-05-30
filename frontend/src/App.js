import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import LaurentIA from "@/pages/LaurentIA";

function App() {
  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LaurentIA />} />
          <Route path="/laurentia" element={<LaurentIA />} />
        </Routes>
      </BrowserRouter>
      <Toaster theme="dark" position="top-center" />
    </div>
  );
}

export default App;
