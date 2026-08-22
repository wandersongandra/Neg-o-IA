$ErrorActionPreference = "Stop"
$env:SOPHIE_API_URL = "http://127.0.0.1:8766"
$env:SOPHIE_WS_URL = "ws://127.0.0.1:8766"
$env:SOPHIE_SERVICE_API_KEY = "test-only-service"
& node.exe "node_modules/next/dist/bin/next" dev -H 127.0.0.1 -p 3000
