# Ultron learning and interface

## Learning model

Ultron does not train model weights from conversation data. A user can explicitly rate an answer and optionally submit a correction. Corrections are embedded locally using the existing deterministic feature-hashing embedder and retrieved for that same authenticated account when semantically relevant.

The `learning.experiences` table uses account ownership, PostgreSQL row-level security, an account-scoped transaction setting, and per-user query filters. The API checks that the referenced conversation belongs to the authenticated user. Users can inspect and delete saved experiences. Credential-like corrections are rejected. Retrieved lessons are untrusted context, never instructions.

The learning migration is `0009_learning_experiences`, after `0008_knowledge_tenant_integrity`. It has not been applied to any database by this change.

## Knowledge boundaries

Knowledge search continues to query documents explicitly added by the signed-in user. This change does not crawl the public web or silently share corrections between accounts. It also fixes the Brain message assembly so retrieved knowledge, memory, and corrections are retained as context after applying the user's configured system prompt.

## Interface

The app is branded as Ultron AI, with a custom vector mechanical face, layered metallic planes, red optical details, CSS perspective/orbit motion, and reduced-motion support. It is an original stylized representation rather than a shipped film still or a rigged 3D character asset.
