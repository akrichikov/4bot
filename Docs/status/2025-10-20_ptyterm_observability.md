## ptyterm Observability Cheatsheet

### Version

```
curl -s http://127.0.0.1:9876/version | jq
```

### Metrics (Prometheus)

```
curl -s http://127.0.0.1:9876/metrics | head -40
```

### Runtime Config

```
curl -s http://127.0.0.1:9876/config | jq
```

### Request Correlation

```
curl -i -H 'X-Request-ID: my-123' http://127.0.0.1:9876/health
```

The server echoes `X-Request-ID` and includes `rid` in audit records for /run, /write, and /read.

