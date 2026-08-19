FROM node:22-alpine AS builder

WORKDIR /app

COPY frontend-react/package.json frontend-react/package-lock.json ./
RUN npm install

COPY frontend-react/ ./

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine

COPY frontend-react/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
