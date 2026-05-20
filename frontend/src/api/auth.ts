import api from "./client";

export const login = async (email: string, password: string) => {
  const res = await api.post("/auth/login", { email, password });
  localStorage.setItem("access_token", res.data.access_token);
  return res;
};

export const signup = (data: {
  email: string;
  password: string;
  name: string;
  gender: "MALE" | "FEMALE";
  birth_date: string;
  phone_number: string;
}) => api.post("/auth/signup", data);

export const logout = () => {
  localStorage.removeItem("access_token");
};

export const getMe = () => api.get("/users/me");
