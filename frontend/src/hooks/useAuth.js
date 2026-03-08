import { useState, useEffect, createContext, useContext } from "react";
import { login as loginApi, register as registerApi } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const saved = localStorage.getItem("user");
    if (token && saved) setUser(JSON.parse(saved));
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    const { data } = await loginApi({ email, password });
    localStorage.setItem("token", data.token);
    // Decode basic user info from JWT payload
    const payload = JSON.parse(atob(data.token.split(".")[1]));
    const userInfo = { email: payload.email, name: payload.unique_name };
    localStorage.setItem("user", JSON.stringify(userInfo));
    setUser(userInfo);
    return userInfo;
  };

  const register = async (email, password, firstName, lastName) => {
    await registerApi({ email, password, firstName, lastName });
    return login(email, password);
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
