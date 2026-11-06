import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App.jsx";
import "./style.css";
import "./extra.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={{ token: { colorPrimary: "#4f46e5", borderRadius: 10, fontFamily: "Inter, 'Noto Sans SC', sans-serif" } }}>
      <BrowserRouter><App /></BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>
);
