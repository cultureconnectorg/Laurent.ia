# syntax=docker/dockerfile:1.7
# Laurent.ia web interface — self-hosted image (G1). Built once, served as static files by Caddy.
FROM node:20-bookworm-slim@sha256:2cf067cfed83d5ea958367df9f966191a942351a2df77d6f0193e162b5febfc0 AS build
WORKDIR /src
COPY package.json ./
# Optional build secret `extra_ca` (TLS-intercepting proxy at build time only; not kept).
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi \
 && yarn install --network-timeout 600000 --non-interactive
COPY . .
# Same origin: the browser calls /api on the same host, through the local reverse proxy.
ENV REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false DISABLE_ESLINT_PLUGIN=true
RUN yarn build

FROM caddy:2.8@sha256:226d1f059b75399fe19182893c7184591c07b97afc8dfcf44eeb80c9a77a530f
COPY --from=build /src/build /srv
