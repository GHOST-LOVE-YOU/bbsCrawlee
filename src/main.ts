import { Configuration, PlaywrightCrawler } from "crawlee";
import { router } from "./routes.js";
import { basicAuth, loadCookies } from "./utils.js";
import express from "express";

const app = express();

let isCrawling = false; // 标志位,表示是否正在爬取

// 在路由上应用身份验证中间件
app.get("/", basicAuth, async (_req, res) => {
  if (isCrawling) {
    return res
      .status(503)
      .json({ message: "Server is busy, please try again later" });
  }

  isCrawling = true; // 设置标志位

  try {
    return res.json({ message: "Welcome to express-app!" });
  } finally {
    isCrawling = false; // 无论成功还是失败,都重置标志位
  }
});

app.listen(8523);
