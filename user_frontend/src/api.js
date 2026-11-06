import axios from "axios";
import { useAuth } from "./store";

export const api = axios.create({ baseURL: "/api", timeout: 20000 });
api.interceptors.request.use((config) => {
  const token = useAuth.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use((response) => response, (error) => {
  if (error.response?.status === 401) useAuth.getState().logout();
  return Promise.reject(error);
});
