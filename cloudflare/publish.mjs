// Builds dist/ from an allowlist of public files, then publishes to Cloudflare.
//   node publish.mjs              build + deploy
//   node publish.mjs --build-only build only (for `npx wrangler dev`)
// Only the files listed here are ever uploaded. Everything else in the repo (secrets.bat,
// family profiles, training data, .cursiv/) stays on this machine.
import { cpSync, mkdirSync, rmSync, writeFileSync, existsSync, realpathSync, lstatSync, readFileSync } from "node:fs";
import { execSync, execFileSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
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
  ["website/local-ai.html", "local-ai.html"],
  ["website/compare.html", "compare.html"],
  ["website/documentation.html", "documentation.html"],
  ["website/local-ai-reference.html", "local-ai-reference.html"],
  ["website/notebook-reference.html", "notebook-reference.html"],
  ["website/portable-ai-reference.html", "portable-ai-reference.html"],
  ["website/ai-reliability-testing.html", "ai-reliability-testing.html"],
  ["website/local-ai-hardware-requirements.html", "local-ai-hardware-requirements.html"],
  ["website/app.html", "app.html"],
  ["website/field-research.html", "field-research.html"],
  ["website/offline-research.html", "offline-research.html"],
  ["website/portable-workspace.html", "portable-workspace.html"],
  ["website/team-drives.html", "team-drives.html"],
  ["website/field-station.html", "field-station.html"],
  ["website/app.webmanifest", "app.webmanifest"],
  ["website/favicon.ico", "favicon.ico"],
  ["website/favicon-96x96.png", "favicon-96x96.png"],
  ["website/apple-touch-icon.png", "apple-touch-icon.png"],
  ["website/llms.txt", "llms.txt"],
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

/favicon.ico
  Content-Type: image/vnd.microsoft.icon

/favicon-96x96.png
  Content-Type: image/png

/apple-touch-icon.png
  Content-Type: image/png

/llms.txt
  Content-Type: text/plain; charset=utf-8

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
  "/local-ai", "/compare", "/documentation",
  "/local-ai-reference", "/notebook-reference", "/portable-ai-reference",
];

// Resolve the destructive build target before removing it; a link must never redirect
// this rebuild outside its owned output directory (OneDrive cloud placeholders are fine).
if (existsSync(dist) && (lstatSync(dist).isSymbolicLink() || realpathSync(dist) !== resolve(dist))) {
  throw new Error(`Unexpected website output target: ${dist}`);
}
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
let fullHistory = false;
try { fullHistory = execFileSync('git', ['rev-parse', '--is-shallow-repository'], { cwd: repo, encoding: 'utf8' }).trim() === 'false'; } catch {}
const sitemap = SITEMAP_URLS.map(path => {
  const file = path === '/' ? 'index.html' : path.endsWith('/') ? `${path.slice(1)}index.html` : `${path.slice(1)}.html`;
  const html = readFileSync(join(dist, file), 'utf8');
  const canonical = [...html.matchAll(/<link\b(?=[^>]*\brel="canonical")[^>]*\bhref="([^"]+)"[^>]*>/g)];
  if (canonical.length !== 1 || canonical[0][1] !== `https://cursiv.us${path}` ||
      /<meta\b(?=[^>]*\bname="robots")(?=[^>]*\bcontent="[^"]*noindex)[^>]*>/i.test(html)) {
    throw new Error(`Sitemap page must be canonical and indexable: ${path}`);
  }
  // Only a known full source history establishes a page's last meaningful commit.
  // Omit optional lastmod in shallow/exported trees rather than inventing today's date.
  let lastmod = '';
  if (fullHistory) {
    const source = PAGES.find(([, target]) => target === file)?.[0] || `website/${file}`;
    const date = execFileSync('git', ['log', '-1', '--format=%cs', '--', source], { cwd: repo, encoding: 'utf8' }).trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(date)) lastmod = `<lastmod>${date}</lastmod>`;
  }
  return `  <url><loc>https://cursiv.us${path}</loc>${lastmod}</url>`;
});
writeFileSync(join(dist, "sitemap.xml"), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${sitemap.join('\n')}\n</urlset>\n`);

console.log(`Built dist/ with ${PAGES.filter(([source]) => source.endsWith('.html')).length} HTML pages + ${FOLDERS.map(f => f[1]).join(", ")} and public discovery files`);

if (!process.argv.includes("--build-only")) {
  execSync("npx wrangler deploy", { cwd: here, stdio: "inherit" });
}
