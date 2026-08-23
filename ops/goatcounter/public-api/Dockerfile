FROM golang:1.25-alpine AS build

WORKDIR /src
COPY go.mod main.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags='-s -w' -o /public-api ./main.go

FROM scratch

COPY --from=build /public-api /public-api
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/public-api"]
