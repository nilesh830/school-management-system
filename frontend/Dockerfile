# ---- Build stage: compile the Angular app ----
FROM node:20-alpine AS build
WORKDIR /app
# package-lock.json is lockfileVersion 3 written by npm 11; node:20-alpine ships
# npm 10, which reads it as out-of-sync and fails `npm ci`. Match the local npm.
RUN npm install -g npm@11
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- Serve stage: Caddy serves static files + proxies /api to the backend ----
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist/sms-frontend/browser /usr/share/caddy
