import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Register from "./pages/Register";
import Identify from "./pages/Identify";
import Directory from "./pages/Directory";
import LostDogs from "./pages/LostDogs";
import "./index.css";

function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/register" element={<Register />} />
        <Route path="/identify" element={<Identify />} />
        <Route path="/directory" element={<Directory />} />
        <Route path="/lost" element={<LostDogs />} />
      </Routes>
    </Router>
  );
}

export default App;
