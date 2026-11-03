# syntax=docker/dockerfile:1
FROM swift:5.10-jammy AS build
WORKDIR /src
COPY Package.swift ./
COPY Sources ./Sources
RUN swift build -c release

FROM swift:5.10-jammy-slim
WORKDIR /app
ENV PORT=8080
COPY --from=build /src/.build/release/App /app/App
EXPOSE 8080
USER nobody
CMD ["/app/App"]
