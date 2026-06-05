import axios from "axios";
import { useAuthStore } from "@/store/authStore";

const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
});

// 401 응답 시 refresh_token 쿠키로 access_token 쿠키 자동 갱신
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      try {
        await axios.get("/api/v1/auth/token/refresh", {
          withCredentials: true,
        });
        return axios(error.config);
      } catch {
        useAuthStore.getState().clear();
        window.location.href = "/";
      }
    }
    return Promise.reject(error);
  },
);

export default api;
