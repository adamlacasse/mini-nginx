# mini-nginx

A tiny learning project that mimics a few core Nginx ideas:

- Serve static files from `./public`
- Reverse proxy `/api/*` requests to a Node backend

## Requirements

- Python 3.10+
- Node.js 18+
- npm

## Run locally

1. Install backend dependencies:

   ```bash
   cd node-app
   npm install
   ```

2. Start the Node backend (Terminal 1):

   ```bash
   cd node-app
   node app.js
   ```

3. Start mini-nginx (Terminal 2):

   ```bash
   python3 mini_nginx.py
   ```

4. Open:

   - `http://127.0.0.1:8080/` (static page)
   - `http://127.0.0.1:8080/api/hello` (proxied API)

## Config

Edit `mini-nginx.json` to change:

- listener host/port
- static root directory
- proxy prefix and backend target
