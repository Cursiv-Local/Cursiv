// Builds dist/ from an allowlist of public files, then publishes to Cloudflare.
//   node publish.mjs              build + deploy
//   node publish.mjs --build-only build only (for `npx wrangler dev`)
// Only the files listed here are ever uploaded. Everything else in the repo (secrets.bat,
// family profiles, training data, .cursiv/) stays on this machine.
import { cpSync, mkdirSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { execSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repo = join(here, "..");
const dist = join(here, "dist");

// [source (relative to repo root), published name]
const PAGES = [
  ["website/index.html", "index.html"],
  ["website/vision.html", "vision.html"],
  ["website/chat.html", "chat.html"],
  ["website/profile.html", "profile.html"],
  ["website/board.html", "board.html"],
  ["website/mailbox.html", "mailbox.html"],
  ["website/start.html", "start.html"],
  ["website/letters.html", "letters.html"],
  ["website/story.html", "story.html"],
  ["website/app.html", "app.html"],
  ["website/app.webmanifest", "app.webmanifest"],
];
const FOLDERS = [["website/assets", "assets"], ["website/notebook", "notebook"]];  // notebook: the offline phone notebook

// The phone notebook (/notebook/) is the only page that may use the GPS and the camera;
// everywhere else both stay off. Its service worker and files are re-checked on each visit.
const HEADERS = `/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), geolocation=()

/notebook/*
  ! Permissions-Policy
  Permissions-Policy: camera=(self), geolocation=(self)
  Cache-Control: no-cache
`;

const ROBOTS = "User-agent: *\nDisallow: /api/\nDisallow: /remote/\n";

rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });

for (const [src, name] of PAGES) {
  const from = join(repo, src);
  if (!existsSync(from)) throw new Error(`Missing page: ${src}`);
  cpSync(from, join(dist, name));
}
for (const [src, name] of FOLDERS) cpSync(join(repo, src), join(dist, name), { recursive: true });
writeFileSync(join(dist, "_headers"), HEADERS);
writeFileSync(join(dist, "robots.txt"), ROBOTS);

console.log(`Built dist/ with ${PAGES.length} pages + ${FOLDERS.map(f => f[1]).join(", ")}`);

if (!process.argv.includes("--build-only")) {
  execSync("npx wrangler deploy", { cwd: here, stdio: "inherit" });
}
