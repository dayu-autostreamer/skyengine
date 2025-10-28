# frontend/Dockerfile
FROM node:18-alpine AS build
WORKDIR /web
COPY frontend/package*.json /web/
RUN npm ci --registry=https://registry.npmmirror.com
COPY frontend /web
RUN npm run build

FROM nginx:alpine AS runtime
# 自定义 Nginx 配置（见下）
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
# 静态资源
COPY --from=build /web/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]