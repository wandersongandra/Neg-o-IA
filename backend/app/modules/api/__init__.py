"""API subpackage.

Keep package initialization free of router imports.  The rate limiter is also
imported by the security router; eagerly importing ``api.router`` here made
that dependency cycle back into the partially initialized security router.
Application composition imports ``api.router`` explicitly from ``main``.
"""
