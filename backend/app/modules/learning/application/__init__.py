"""Casos de uso do módulo learning — pipeline de aprendizado contínuo.

v0: esqueleto. Em v2+ implementa o pipeline assíncrono por lote:
normalizar → analisar → sumarizar → classificar → relacionar →
deduplicar → salvar → efeitos colaterais (janelas de consolidação).
"""
