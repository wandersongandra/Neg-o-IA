"""Casos de uso do módulo scheduler — agendamento e execução de jobs.

v0: esqueleto. Em v2+ implementa o agendador (cron, recorrência,
one-shot) com persistência e recuperação pós-reboot, publicando
`scheduler.tick` para Automation/Monitoring.
"""
