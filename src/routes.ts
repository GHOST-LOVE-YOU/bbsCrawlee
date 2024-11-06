import { createPlaywrightRouter } from "crawlee";
import { addPostsToQueue, handleAuth, getPostDetails } from "./utils.js";

export const router = createPlaywrightRouter();

router.addHandler("DETAIL", async ({ page, log, session, enqueueLinks, crawler }) => {
  if (session) {
    await handleAuth(page, log, session);
  }

  const postDatas = await getPostDetails(page);
  log.debug(JSON.stringify(postDatas, null, 2));
  log.debug("a detail page");
  
  // Store postDatas in the crawler's default storage
  await crawler.pushData(postDatas);

  await enqueueLinks({
    selector: 'li.page-normal a[title="下一页"]',
    label: "DETAIL",
  });
});

router.addDefaultHandler(async ({ page, enqueueLinks, log, session }) => {
  if (session) {
    await handleAuth(page, log, session);
  }
  const overpage = await addPostsToQueue(page, enqueueLinks);

  if (!overpage) {
    await page.waitForSelector('a[title="下一页"]');
    const nextPageLink = await page.$('a[title="下一页"]');
    if (nextPageLink) {
      // 获取链接的 href 属性
      const nextPageUrl = await nextPageLink.evaluate(
        (node: HTMLAnchorElement) => node.href
      );

      // 将下一页的 URL 加入队列
      await enqueueLinks({
        urls: [nextPageUrl],
      });
    }
  }
});
