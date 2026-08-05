"""Adaptadores do módulo scheduler — motor de cron e persistência.

v0: esqueleto. Em v2+ implementa o motor de agendamento (ex.:
APScheduler) com journaling, persistência em Postgres e recuperação
de tarefas perdidas pós-reboot.
"""
