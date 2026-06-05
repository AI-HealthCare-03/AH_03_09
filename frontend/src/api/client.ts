import axios from "axios";
import { useAuthStore } from "@/store/authStore";

const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
});

// 요청마다 authStore의 accessToken을 Bearer 헤더에 포함
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 응답 시 refresh token으로 자동 재발급
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      try {
        const res = await axios.get("/api/v1/auth/token/refresh", {
          withCredentials: true,
        });
        const newToken = res.data.access_token;
        useAuthStore.getState().setToken(newToken);
        error.config.headers.Authorization = `Bearer ${newToken}`;
        return axios(error.config);
      } catch {
        useAuthStore.getState().clear();
        window.location.href = "/";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
