import { crawlComment, crawlPost } from "./type.js";
import { PlaywrightCrawlingContext, Log, Session } from "crawlee";
import { Page } from "playwright";
import { Request, Response, NextFunction } from "express";
import dotenv from "dotenv";
import path from "path";
import { dirname } from "path";
import { fileURLToPath } from "url";
import fs from "fs/promises";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Now you can use __dirname
dotenv.config({ path: path.resolve(__dirname, "../.env") });

// 从环境变量中获取用户名和密码
const USERNAME = process.env.BBS_USERNAME || "";
const PASSWORD = process.env.BBS_PASSWORD || "";
const AUTH_USERNAME = process.env.AUTH_USERNAME || "";
const AUTH_PASSWORD = process.env.AUTH_PASSWORD || "";

// 添加基本的身份验证中间件
export const basicAuth = (req: Request, res: Response, next: NextFunction) => {
  // 这里使用 Buffer 来解码 base64 编码的认证信息
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    res.setHeader("WWW-Authenticate", 'Basic realm="Restricted Area"');
    return res.status(401).json({ message: "Authentication required." });
  }

  const auth = Buffer.from(authHeader.split(" ")[1], "base64")
    .toString()
    .split(":");
  const user = auth[0];
  const pass = auth[1];

  // 在这里设置你的用户名和密码
  if (user === AUTH_USERNAME && pass === AUTH_PASSWORD) {
    return next();
  } else {
    res.setHeader("WWW-Authenticate", 'Basic realm="Restricted Area"');
    return res.status(401).json({ message: "Authentication failed." });
  }
};

export const handleAuth = async (page: Page, log: Log, session: Session) => {
  const isLoginPage = await page.$("#u_login_form").then(Boolean);
  if (isLoginPage) {
    log.info("Login page detected, logging in...");
    await page.fill("#u_login_id", USERNAME);
    await page.fill("#u_login_passwd", PASSWORD);
    await page.click("#u_login_submit");

    await Promise.race([
      page.waitForSelector(".a-content-wrap"),
      page.waitForTimeout(10000),
    ]);

    // Save cookies to the session after successful login
    const cookies = await page.context().cookies();
    session.setCookies(cookies, page.url());

    // Save cookies to a JSON file
    await fs.writeFile(
      path.join(__dirname, "cookie.json"),
      JSON.stringify(cookies, null, 2),
      "utf8",
    );
    log.info("Cookies saved to cookie.json");
  }
};

export const loadCookies = async (
  crawlingContext: PlaywrightCrawlingContext,
) => {
  try {
    const cookiesData = await fs.readFile(
      path.join(__dirname, "cookie.json"),
      "utf-8",
    );
    const cookies = JSON.parse(cookiesData);
    const typedCookies = cookies.map((cookie: any) => ({
      ...cookie,
      sameSite: cookie.sameSite as "Lax" | "Strict" | "None",
    }));
    await crawlingContext.page.context().addCookies(typedCookies);
  } catch (error: any) {
    if (error.code === "ENOENT") {
      console.warn(
        "Warning: ./cookie.json file not found. Proceeding without adding cookies.",
      );
    } else {
      console.error("Error reading or parsing cookie file:", error);
    }
  }
};

export const addPostsToQueue = async (page: Page, enqueueLinks: any) => {
  const currentDateTime = new Date();
  const posts = await page.$$eval("tr", (rows) =>
    rows.map((row) => {
      const replyTimeText =
        row
          .querySelector('td.title_10 a[title="跳转至最后回复"]')
          ?.textContent?.trim() || "";
      const url =
        row
          .querySelector('td.title_9 a[href^="/article/IWhisper/"]')
          ?.getAttribute("href") || "";
      return { replyTimeText, url };
    }),
  );

  let overpage = false;

  for (const post of posts) {
    if (post.url && post.replyTimeText) {
      const replyTime = new Date(
        `${currentDateTime.toDateString()} ${post.replyTimeText}`,
      );
      const timeDifferenceMs = currentDateTime.getTime() - replyTime.getTime();
      const timeDifferenceMinutes = timeDifferenceMs / 60000;

      if (isNaN(timeDifferenceMinutes)) {
        continue;
      }

      if (timeDifferenceMinutes <= 10) {
        const absoluteUrl = new URL(post.url, "https://bbs.byr.cn").toString();
        await enqueueLinks({
          urls: [absoluteUrl],
          label: "DETAIL",
          transformRequestFunction: (request: {
            url: string;
            uniqueKey?: string;
          }) => {
            request.uniqueKey = `${request.url}#${Date.now()}`;
            return request;
          },
        });
      } else {
        overpage = true;
        break;
      }
    }
  }

  return overpage;
};

export const getPostDetails = async (page: Page) => {
  const postDatas: crawlPost = {
    byr_id: "",
    topic: "",
    author: "",
    time: "",
    page: "",
    comments: [],
  };

  const postId = page.url().match(/\/#!article\/IWhisper\/(\d+)/)?.[1] || "";

  const postTopicElement = await page.$("div.b-head.corner span.n-left");
  const postTopicText = (await postTopicElement?.innerText()) || "";
  const postTopic = postTopicText.replace(/^文章主题:\s*/, "").trim();

  const urlMatch = page.url().match(/\/article\/IWhisper\/\d+\?p=(\d+)/);
  const postPage = urlMatch ? urlMatch[1] : "1";

  postDatas.byr_id = postId;
  postDatas.topic = postTopic;
  postDatas.page = postPage;

  const comments = await getComments(page);
  postDatas.author = postPage === "1" ? comments[0]?.author : "unknown";
  postDatas.time = postPage === "1" ? comments[0]?.time : "unknown";
  postDatas.comments = comments;

  return postDatas;
};

export const getComments = async (page: Page) => {
  const comments: crawlComment[] = [];
  const commentElements = await page.$$(
    "div.b-content.corner div.a-wrap.corner table.article tbody",
  );

  for (const wrap of commentElements) {
    let floorElement = await wrap.$("tr.a-head td a.a-func-collect span.a-pos");
    if (!floorElement) {
      floorElement = await wrap.$("tr.a-head td span.a-pos");
    }
    const floor = (await floorElement?.innerText()) || "";

    let wrapElement = await wrap.$("tr.a-body td.a-content div.a-content-wrap");
    if (!wrapElement) {
      // 无头浏览器应该不会出现hide的状态, 不用处理
      continue;
    }
    const wrapHtml = await wrapElement.innerHTML();

    const author = wrapHtml.match(/发信人: (.+?) \(/)?.[1] || "";
    const section = wrapHtml.match(/信区: (\w+)/)?.[1] || "";
    const timeStr = wrapHtml.match(/发信站: .*? \((.*?)\)/)?.[1] || "";

    let content = wrapHtml.match(/<br><br>(.+?)<br>--/)?.[1] || " ";

    let likesElement, dislikesElement;
    if (floor === "楼主") {
      likesElement = await wrap.$(
        "tr.a-bottom td ul.a-status li a.a-func-support",
      );
      dislikesElement = await wrap.$(
        "tr.a-bottom td ul.a-status li a.a-func-oppose",
      );
    } else {
      likesElement = await wrap.$(
        "tr.a-bottom td ul.a-status li a.a-func-like",
      );
      dislikesElement = await wrap.$(
        "tr.a-bottom td ul.a-status li a.a-func-cai",
      );
    }

    const likesText = (await likesElement?.innerText()) || "";
    const dislikesText = (await dislikesElement?.innerText()) || "";

    const likes = parseInt(likesText.match(/\((?:\+)?(\d+)\)/)?.[1] || "0");
    const dislikes = parseInt(
      dislikesText.match(/\((?:\+)?(\d+)\)/)?.[1] || "0",
    );

    const commentData = {
      floor,
      author,
      section,
      content,
      like: likes,
      dislike: dislikes,
      time: timeStr,
    };
    comments.push(commentData);
  }
  return comments;
};
