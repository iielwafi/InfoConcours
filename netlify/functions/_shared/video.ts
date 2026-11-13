const YOUTUBE_ID = /^[A-Za-z0-9_-]{11}$/;

/** Extract a real 11-character YouTube video ID from supported YouTube URL forms. */
export function extractYoutubeVideoId(raw: string): string | null {
  try {
    const url = new URL(raw.trim());
    const host = url.hostname.toLowerCase().replace(/^www\./, "");
    if (host === "youtu.be") {
      const candidate = url.pathname.split("/").filter(Boolean)[0] ?? "";
      return YOUTUBE_ID.test(candidate) ? candidate : null;
    }
    if (host !== "youtube.com" && host !== "m.youtube.com" && host !== "youtube-nocookie.com") {
      return null;
    }
    const path = url.pathname.split("/").filter(Boolean);
    const candidate = url.pathname === "/watch"
      ? url.searchParams.get("v") ?? ""
      : path.length >= 2 && ["embed", "shorts", "live"].includes(path[0])
        ? path[1]
        : "";
    return YOUTUBE_ID.test(candidate) ? candidate : null;
  } catch {
    return null;
  }
}

export function validHttpsThumbnail(raw: string): boolean {
  if (!raw.trim()) return true;
  try {
    const url = new URL(raw.trim());
    return url.protocol === "https:" && Boolean(url.hostname) && !url.username && !url.password;
  } catch {
    return false;
  }
}
