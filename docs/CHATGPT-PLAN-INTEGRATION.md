# Conectar uma conta ChatGPT ao agente

O agente pode usar **Sign in with ChatGPT (SIWC)** para chamar a Responses API em nome de uma conta ChatGPT elegível. Isso é separado de uma chave de API e do faturamento da API. O plano precisa aparecer como elegível durante o consentimento da OpenAI; a implementação não consegue inspecionar nem contornar essa decisão.

A integração é destinada a uma instalação própria do Neg-o-IA. A documentação da OpenAI descreve acesso para clientes locais/auto-hospedados e exige aprovação para determinados aplicativos hospedados ou pagos. Este repositório ainda não contém um arquivo `LICENSE`; o responsável pelo projeto precisa escolher e aprovar uma licença compatível antes de afirmar que o cliente atende ao requisito de software aberto.

## Preparar a instalação

1. Gere uma chave exclusiva para os tokens OAuth:

   ```bash
   cd backend
   uv run python -m app.cli generate-oauth-encryption-key
   ```

2. Guarde o valor fora do repositório como `secrets/oauth_credential_encryption_key`, com permissões `0600`. Não reutilize `NEGAO_SECRET_KEY` nem uma chave de backup.
3. Aplique a migration `0011_openai_chatgpt_plan` durante a implantação. Em produção, use o processo de release habitual para executar `alembic upgrade head` antes de iniciar esta versão.
4. Publique backend e frontend que contenham as rotas de conexão. O frontend precisa estar servido por HTTPS em produção.

A chave é necessária para iniciar o backend. Perder ou trocar a chave torna credenciais já guardadas ilegíveis; faça backup seguro junto com os demais segredos.

## Autorizar a conta

Na tela **Configuração da Ultron**, copie o comando apresentado e execute-o a partir da raiz de um checkout desta versão do projeto, em um computador com `uv` e navegador. O comando:

- autentica o usuário do agente pela sessão de navegador protegida por cookie `HttpOnly`;
- inicia o callback OAuth apenas em `127.0.0.1` e usa `state`, `nonce` e PKCE;
- abre a página de consentimento da OpenAI;
- valida a assinatura e as claims do ID token antes do envio;
- transmite os tokens ao domínio HTTPS do agente e encerra a sessão local ao final.

A senha do ChatGPT nunca é solicitada. A senha digitada é apenas a da conta local do agente e é enviada ao endpoint de login HTTPS do próprio app. O terminal não grava tokens em arquivo. O callback termina no computador em que o comando roda; em implantação remota, o callback OAuth não precisa ser encaminhado para o servidor.

Depois da autorização, atualize o status na interface, escolha **Plano ChatGPT conectado** e selecione um modelo retornado pela própria conta. O modo ChatGPT não cai silenciosamente para NVIDIA/mock se a conta estiver desconectada ou sem permissão.

## Limites atuais

- Somente texto via Responses API, em streaming, com `store: false`.
- A interface consulta o catálogo de modelos por conta; a conta pode não ter modelos visíveis.
- Áudio, vídeo, arquivos, endpoint de transcrição, ferramentas da Responses API, `temperature` e `max_output_tokens` não são encaminhados por esta integração.
- O comportamento da integração e os modelos disponíveis podem mudar durante a prévia de SIWC. O consentimento, a elegibilidade da conta e eventuais limites de uso são controlados pela OpenAI.
- Para chamadas de API com uma chave de API, continua sendo necessário faturamento separado da API.

## Dados e isolamento

Tokens de acesso/renovação e o identificador opaco da conta ficam cifrados com AES-256-GCM usando chave dedicada e AAD associada ao ID do usuário e ao tipo do campo. O ID token é validado e descartado; a senha ChatGPT e as conversas ChatGPT não são armazenadas. O PostgreSQL ativa e força RLS na tabela de credenciais; a política permite somente a identidade autenticada em `app.user_id`. O banco não recebe tokens em claro. Logs e status da interface não retornam tokens. Reconexões reutilizam o client ID existente e conferem a mesma conta. Para trocar de conta, desconecte a anterior na interface antes de autorizar a nova. Desconectar remove a credencial local e tenta revogá-la junto à OpenAI; a remoção local ocorre mesmo se a revogação remota não confirmar.

O host ID persistente identifica esta instalação do agente para o cliente OAuth. Ele não é um segredo de autenticação.

## Modelo 3D original

O avatar WebGL usa o modelo articulado `frontend/public/models/sentinel.glb`, produzido pelo script `frontend/scripts/create_sentinel_model.py`. Para regenerar o GLB e a imagem WebP de contingência, execute `frontend/scripts/build-sentinel-asset.sh` em uma máquina com Blender e Pillow instalados. O avatar acompanha movimento do ponteiro e move a mandíbula com o áudio sintetizado; em dispositivos sem WebGL, mostra a renderização estática.
