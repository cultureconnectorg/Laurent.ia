# syntax=docker/dockerfile:1.7
# Laurent.ia web interface — self-hosted image (G1). Built once, served as static files by Caddy.
FROM node:20-bookworm-slim AS build
WORKDIR /src
COPY package.json ./
# Optional build secret `extra_ca` (TLS-intercepting proxy at build time only; not kept).
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi \
 && yarn install --network-timeout 600000 --non-interactive
COPY . .
# Same origin: the browser calls /api on the same host, through the local reverse proxy.
ENV REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false DISABLE_ESLINT_PLUGIN=true
RUN yarn build

FROM caddy:2.8
COPY --from=build /src/build /srv
