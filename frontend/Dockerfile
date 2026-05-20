FROM node:20-alpine AS builder
WORKDIR /app
COPY .npmrc* ./
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM alpine:latest
COPY --from=builder /app/dist /dist
HEALTHCHECK --interval=2s --timeout=5s --retries=10 CMD test -f /vol/web/frontend/index.html || exit 1
CMD ["sh", "-c", "cp -r /dist/. /vol/web/frontend/ && tail -f /dev/null"]
