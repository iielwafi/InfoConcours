import test from "node:test";
import assert from "node:assert/strict";
import { CURATED_FRENCH_VIDEOS, MISSING_FRENCH_VIDEO_LESSONS } from "../netlify/functions/_shared/curated-videos.ts";

test("curated French lesson videos contain valid unique YouTube IDs and lesson names", () => {
  assert.equal(CURATED_FRENCH_VIDEOS.length, 28);
  const ids = CURATED_FRENCH_VIDEOS.map((video) => video.videoId);
  const titles = CURATED_FRENCH_VIDEOS.map((video) => video.lessonTitle);
  assert.equal(new Set(ids).size, ids.length);
  assert.equal(new Set(titles).size, titles.length);
  for (const video of CURATED_FRENCH_VIDEOS) {
    assert.match(video.videoId, /^[A-Za-z0-9_-]{11}$/);
    assert.ok(video.title.length > 5);
    assert.ok(video.channel.length > 1);
    assert.ok(video.description.length > 20);
  }
});

test("only explicitly researched gaps remain outside the import pack", () => {
  assert.deepEqual([...MISSING_FRENCH_VIDEO_LESSONS], [
    "Comparer cache, RAM et stockage",
    "Comparer sans se fier à un seul chiffre",
    "Choisir un format d’image",
    "Comprendre couleur et taille d’image",
  ]);
  const importedTitles = new Set(CURATED_FRENCH_VIDEOS.map((video) => video.lessonTitle));
  for (const title of MISSING_FRENCH_VIDEO_LESSONS) assert.ok(!importedTitles.has(title));
});
