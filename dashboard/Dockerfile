# Multi-stage: build the static Vite bundle, then serve it with nginx --
# the built output is a handful of static files, no Node runtime needed
# once built.

FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# Vite env vars are baked in at BUILD time, not read at container runtime
# (this is Vite's own design, not a TRACE choice) -- so this has to be a
# build ARG, and the dashboard image must be rebuilt (not just restarted)
# after changing VITE_API_BASE_URL. docker-compose.yml passes this through
# from the same .env the rest of the stack reads.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
