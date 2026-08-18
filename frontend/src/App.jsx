import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import InstallPrompt from "./components/InstallPrompt";
import UpdatePrompt from "./components/UpdatePrompt";
import Home from "./pages/Home";
import Register from "./pages/Register";
import Identify from "./pages/Identify";
import Directory from "./pages/Directory";
import LostDogs from "./pages/LostDogs";
import FoundIntake from "./pages/FoundIntake";
import ReportLost from "./pages/ReportLost";
import Staff from "./pages/Staff";
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
        <Route path="/found" element={<FoundIntake />} />
        <Route path="/report-lost/:dogId" element={<ReportLost />} />
        <Route path="/staff" element={<Staff />} />
      </Routes>
      <Footer />
      <UpdatePrompt />
      <InstallPrompt />
    </Router>
  );
}

export default App;
