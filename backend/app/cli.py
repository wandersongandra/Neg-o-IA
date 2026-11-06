"""CLI administrativa da Ultron para operações de bootstrap seguras."""

from __future__ import annotations

import argparse
import asyncio
import base64
import getpass
import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.infrastructure.db import create_engine, create_session_factory
from app.modules.brain.siwc_client import SiwcError, connect_chatgpt_plan
from app.modules.configuration.settings import get_settings
from app.modules.database.infrastructure import UserORM
from app.modules.security.application.identity import create_user


def _read_password() -> str:
    password = getpass.getpass("Senha (mínimo 12 caracteres): ")
    confirmation = getpass.getpass("Confirme a senha: ")
    if password != confirmation:
        raise ValueError("as senhas não coincidem")
    if len(password) < 12:
        raise ValueError("a senha precisa ter pelo menos 12 caracteres")
    return password


async def _create_user(username: str, display_name: str | None, password: str) -> int:
    normalized = username.strip().lower()
    if len(normalized) < 3 or len(normalized) > 128:
        print("ERRO: usuário deve ter entre 3 e 128 caracteres.")
        return 2

    factory = create_session_factory(create_engine(get_settings().database_url))
    try:
        async with factory() as session:
            existing = await session.execute(
                select(UserORM.id).where(UserORM.username == normalized)
            )
            if existing.scalar_one_or_none() is not None:
                print("ERRO: usuário já existe.")
                return 3
            identity = await create_user(
                session,
                normalized,
                password,
                display_name=display_name,
            )
            await session.commit()
    except IntegrityError:
        print("ERRO: usuário já existe.")
        return 3
    except SQLAlchemyError:
        print("ERRO: banco de dados indisponível.")
        return 4

    print(f"Usuário criado com sucesso: {identity.username} ({identity.user_id})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Administração segura da Ultron")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser(
        "create-user",
        help="Cria um usuário sem habilitar o endpoint público de registro.",
    )
    create.add_argument("--username", required=True)
    create.add_argument("--display-name", default=None)

    chatgpt = subparsers.add_parser(
        "connect-chatgpt-plan",
        help="Autoriza um plano ChatGPT elegível por OAuth e envia os tokens cifrados ao agente.",
    )
    chatgpt.add_argument("--api-url", required=True, help="URL raiz da API do agente.")
    chatgpt.add_argument("--username", default=None, help="Usuário local da Ultron.")

    subparsers.add_parser(
        "generate-oauth-encryption-key",
        help="Gera uma chave aleatória de 256 bits para cifrar tokens OAuth no banco.",
    )

    args = parser.parse_args()
    if args.command == "connect-chatgpt-plan":
        try:
            return connect_chatgpt_plan(api_url=str(args.api_url), username=args.username)
        except SiwcError as exc:
            print(f"ERRO: {exc}")
            return 5
    if args.command == "generate-oauth-encryption-key":
        print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("="))
        return 0

    try:
        password = _read_password()
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return 2

    return asyncio.run(
        _create_user(
            username=str(args.username),
            display_name=str(args.display_name) if args.display_name else None,
            password=password,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
