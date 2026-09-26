export function buildContentSecurityPolicy(
  nonce: string,
  production: boolean,
): string {
  const directives = [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "frame-src 'none'",
    "form-action 'self'",
    [
      "script-src",
      "'self'",
      `'nonce-${nonce}'`,
      "'strict-dynamic'",
      ...(production ? [] : ["'unsafe-eval'"]),
    ].join(" "),
    "script-src-attr 'none'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "media-src 'self' data: blob:",
    production ? "connect-src 'self' wss:" : "connect-src 'self' ws: wss:",
    "worker-src 'self' blob:",
    "manifest-src 'self'",
    ...(production ? ["upgrade-insecure-requests"] : []),
  ];

  return directives.join("; ");
}
