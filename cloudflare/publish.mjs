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
  ["website/404.html", "404.html"],
  ["website/index.html", "index.html"],
  ["website/vision.html", "vision.html"],
  ["website/chat.html", "chat.html"],
  ["website/profile.html", "profile.html"],
  ["website/start.html", "start.html"],
  ["website/testers.html", "testers.html"],
  ["website/story.html", "story.html"],
  ["website/open-source-offline-ai.html", "open-source-offline-ai.html"],
  ["website/ai-reliability-testing.html", "ai-reliability-testing.html"],
  ["website/local-ai-hardware-requirements.html", "local-ai-hardware-requirements.html"],
  ["website/app.html", "app.html"],
  ["website/field-research.html", "field-research.html"],
  ["website/offline-research.html", "offline-research.html"],
  ["website/portable-workspace.html", "portable-workspace.html"],
  ["website/team-drives.html", "team-drives.html"],
  ["website/field-station.html", "field-station.html"],
  ["website/app.webmanifest", "app.webmanifest"],
];
const FOLDERS = [["website/assets", "assets"], ["website/notebook", "notebook"], ["website/privacy", "privacy"]];  // notebook and privacy policy directory routes

// The phone notebook (/notebook/) is the only page that may use the GPS and the camera;
// everywhere else both stay off. Its service worker and files are re-checked on each visit.
// /testers uses no scripts or external resources. Every page sends no-transform, which
// stops Cloudflare from inserting its automatic Web Analytics beacon or email
// obfuscation into the HTML, so visitors get exactly the files published here:
// https://developers.cloudflare.com/web-analytics/faq/
const HEADERS = `/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), geolocation=()
  Cache-Control: public, max-age=0, must-revalidate, no-transform

/testers
  Content-Security-Policy: default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'; script-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'self'; frame-ancestors 'none'

/testers/
  Content-Security-Policy: default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'; script-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'self'; frame-ancestors 'none'

/testers.html
  Content-Security-Policy: default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'; script-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'self'; frame-ancestors 'none'

/notebook/*
  ! Permissions-Policy
  Permissions-Policy: camera=(self), geolocation=(self)
  ! Cache-Control
  Cache-Control: no-cache, no-transform
`;

const ROBOTS = "User-agent: *\nDisallow: /api/\nDisallow: /remote/\nDisallow: /admin/\nSitemap: https://cursiv.us/sitemap.xml\n";
const SITEMAP_URLS = [
  "/", "/field-research", "/team-drives", "/field-station", "/offline-research", "/portable-workspace", "/start", "/vision", "/story", "/open-source-offline-ai",
  "/ai-reliability-testing", "/local-ai-hardware-requirements", "/privacy/", "/testers",
];

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
writeFileSync(join(dist, "sitemap.xml"), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${SITEMAP_URLS.map((path) => `  <url><loc>https://cursiv.us${path}</loc></url>`).join("\n")}\n</urlset>\n`);

console.log(`Built dist/ with ${PAGES.length} pages + ${FOLDERS.map(f => f[1]).join(", ")}`);

if (!process.argv.includes("--build-only")) {
  execSync("npx wrangler deploy", { cwd: here, stdio: "inherit" });
}
