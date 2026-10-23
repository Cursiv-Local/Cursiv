---
title: Start a React website with Vite (Node.js)
triggers: react|vite|node|npm|javascript app|frontend|typescript|web page|website
---
## Question
How do I start a React website?

## Answer
**Where:** PowerShell (WSL notes in brackets).

### One-time: install Node.js
```powershell
winget install OpenJS.NodeJS.LTS
```
Close and reopen PowerShell, then check (should print versions):
```powershell
node -v
```
```powershell
npm -v
```
[WSL: install nvm — `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash`, reopen the terminal, `nvm install --lts`. Never `sudo npm`.]

### Create the project
```powershell
cd $HOME\projects
```
```powershell
npm create vite@latest my-site -- --template react
```
```powershell
cd my-site
```
```powershell
npm install
```

### Run it while you work
```powershell
npm run dev
```
**Success:** it prints `Local: http://localhost:5173/`. Open it; edit `src/App.jsx`, save, and the page updates instantly. Stop with Ctrl+C.

### Every new terminal
`cd $HOME\projects\my-site` then `npm run dev`. (No venv-style activation for Node; `npm install` again only after pulling new dependencies.)

### Build for publishing
```powershell
npm run build
```
The finished site is in `dist/` — upload that folder to Cloudflare Pages, Netlify or GitHub Pages.

### If something goes wrong
- `npm is not recognized` → reopen the terminal after installing Node.
- `npm ... running scripts is disabled` → `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Port 5173 busy → Vite picks the next free port automatically; read the URL it prints.
- Blank page → open the browser console (F12) and read the red error.
