# Build from the REPO ROOT (the bot shares web/lib and the data artifact):
#   docker build -f bot/Dockerfile -t kargin-bot .
FROM node:20-slim AS build
WORKDIR /app
COPY bot/package.json bot/package-lock.json bot/
RUN cd bot && npm ci
COPY bot/tsconfig.json bot/
COPY bot/src bot/src
COPY web/lib web/lib
RUN cd bot && npm run build

FROM node:20-slim
WORKDIR /app
ENV NODE_ENV=production
COPY bot/package.json bot/package-lock.json bot/
RUN cd bot && npm ci --omit=dev
COPY --from=build /app/bot/dist bot/dist
# The same artifact the website bundles; refreshed by rebuilding the image.
COPY web/public/data/sketches.json web/public/data/sketches.json
USER node
# Cloud Run injects PORT; WEBHOOK_URL switches the bot into webhook mode.
CMD ["node", "bot/dist/index.js"]
