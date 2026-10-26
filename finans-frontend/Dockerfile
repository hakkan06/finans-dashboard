# 1) Derleme: React arayüzü statik dosyalara dönüştürülür
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY build.mjs index.template.html ./
COPY src ./src
COPY public ./public
RUN node build.mjs

# 2) Sunum: nginx statik dosyaları verir, /api isteklerini backend'e iletir
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1/healthz || exit 1
