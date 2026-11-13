import test from "node:test";
import assert from "node:assert/strict";
import { extractYoutubeVideoId, validHttpsThumbnail } from "../netlify/functions/_shared/video.ts";

test("extracts video IDs from YouTube watch, short, embed, shorts and live URLs", () => {
  const id = "dQw4w9WgXcQ";
  for (const url of [
    `https://www.youtube.com/watch?v=${id}`,
    `https://youtu.be/${id}`,
    `https://www.youtube.com/embed/${id}`,
    `https://youtube.com/shorts/${id}`,
    `https://youtube.com/live/${id}`,
    `https://www.youtube-nocookie.com/embed/${id}`,
  ]) assert.equal(extractYoutubeVideoId(url), id);
});

test("rejects non-YouTube hosts, malformed IDs, and invalid URLs", () => {
  assert.equal(extractYoutubeVideoId("https://youtube.com.evil.test/watch?v=dQw4w9WgXcQ"), null);
  assert.equal(extractYoutubeVideoId("https://example.com/watch?v=dQw4w9WgXcQ"), null);
  assert.equal(extractYoutubeVideoId("https://youtube.com/watch?v=short"), null);
  assert.equal(extractYoutubeVideoId("not a URL"), null);
});

test("thumbnail URL validation only accepts optional credential-free HTTPS URLs", () => {
  assert.equal(validHttpsThumbnail(""), true);
  assert.equal(validHttpsThumbnail("https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"), true);
  assert.equal(validHttpsThumbnail("http://example.com/image.jpg"), false);
  assert.equal(validHttpsThumbnail("https://user:pass@example.com/image.jpg"), false);
});
