FROM node:22-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev || npm install --omit=dev
COPY server.js ./
ENV PORT=3000 NODE_ENV=production
USER node
EXPOSE 3000
CMD ["node", "server.js"]
