export type crawlComment = {
  author: string;
  content: string;
  floor: string;
  like: number;
  dislike: number;
  time: string;
};

export type crawlPost = {
  byr_id: string;
  topic: string;
  author: string;
  time: string;
  page: string;
  comments: crawlComment[];
};
