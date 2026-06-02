import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
});

// 요청마다 localStorage의 access_token을 Bearer 헤더에 포함
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
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
        localStorage.setItem("access_token", newToken);
        error.config.headers.Authorization = `Bearer ${newToken}`;
        return axios(error.config);
      } catch {
        localStorage.removeItem("access_token");
        window.location.href = "/";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
