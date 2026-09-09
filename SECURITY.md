# Política de Segurança

A Sophie integra autenticação, memória, voz, serviços externos, PostgreSQL e Redis. Falhas de segurança devem ser tratadas de forma privada e responsável.

## Relato de vulnerabilidades

Não publique em issues públicas credenciais, tokens, dados pessoais, prompts privados, detalhes de exploração, dumps, cookies ou vulnerabilidades ainda não corrigidas.

Ao identificar uma possível falha, utilize um canal privado de contato com o mantenedor indicado no perfil do GitHub e informe, quando possível:

- componente afetado;
- descrição objetiva do problema;
- passos mínimos para reprodução;
- impacto potencial;
- evidências sem dados sensíveis;
- sugestão de mitigação ou correção.

## Segredos e integrações

Credenciais de APIs, chaves de modelo, tokens, arquivos `.env`, URLs privadas de banco, cookies, chaves de sessão e dados de produção não devem ser versionados.

Variáveis de exemplo devem conter apenas placeholders fictícios.

## Dependências e supply chain

Dependências com vulnerabilidades de severidade alta ou crítica devem ser avaliadas antes de promoção para produção. Mudanças em autenticação, autorização, memória, ferramentas/agentes e integrações externas exigem atenção especial.

## Divulgação

Detalhes técnicos devem permanecer privados até que exista correção ou mitigação adequada.
