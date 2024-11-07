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
    const crawler = new PlaywrightCrawler({
      requestHandler: async ({ page }) => {
        // Wait for the actor cards to render.
        await page.waitForSelector(".collection-block-item");
        // Execute a function in the browser which targets
        // the actor card elements and allows their manipulation.
        const categoryTexts = await page.$$eval(
          ".collection-block-item",
          (els) => {
            // Extract text content from the actor cards
            return els.map((el) => el.textContent);
          },
        );
        categoryTexts.forEach((text, i) => {
          console.log(`CATEGORY_${i + 1}: ${text}\n`);
        });
      },
    });

    await crawler.run([
      "https://warehouse-theme-metal.myshopify.com/collections",
    ]);
    return res.json({ message: "Welcome to express-app!" });
  } finally {
    isCrawling = false; // 无论成功还是失败,都重置标志位
  }
});

app.listen(8523);
