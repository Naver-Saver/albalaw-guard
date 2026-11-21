FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx/http.conf nginx/https.conf /etc/nginx/albalaw/
COPY nginx/http.conf /etc/nginx/conf.d/default.conf
COPY nginx/40-albalaw-tls.sh /docker-entrypoint.d/40-albalaw-tls.sh
RUN chmod 755 /docker-entrypoint.d/40-albalaw-tls.sh
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80 443
