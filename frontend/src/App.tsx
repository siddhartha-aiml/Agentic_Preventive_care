import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { LoaderCircle } from "lucide-react";
import { useAuth } from "./lib/auth";
import type { Role } from "./lib/api";
import Landing from "./pages/Landing";
import { Login, Register } from "./pages/Auth";
import Workspace from "./pages/Workspace";
import Chat from "./pages/Chat";
import Appointments from "./pages/Appointments";
import Profile from "./pages/Profile";
import Doctor from "./pages/Doctor";

function Protected({ role, children }: { role: Role; children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex h-dvh items-center justify-center"><LoaderCircle className="h-8 w-8 animate-spin text-brand-500" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to={user.role === "doctor" ? "/doctor" : "/app"} replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/app" element={<Protected role="patient"><Workspace /></Protected>}>
        <Route index element={<Chat />} />
        <Route path="c/:id" element={<Chat />} />
        <Route path="appointments" element={<Appointments />} />
        <Route path="profile" element={<Profile />} />
      </Route>
      <Route path="/doctor" element={<Protected role="doctor"><Doctor /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
