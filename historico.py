"""Lê as rodadas anteriores em resultados/ para saber quais anúncios já foram mostrados."""
import re

NOME_ARQUIVO = re.compile(r"rodada_\d{4}-\d{2}-\d{2}_\d{2}h\d{2}\.txt$")
LINHA_SITE = re.compile(r"^Site:\s+(.+?) \(código (\S+)\)", re.M)


def carregar(pasta, grupo_do_site):
    """Retorna o conjunto de (grupo, código) dos anúncios que já saíram em alguma rodada.

    `grupo_do_site` mapeia o nome do site no arquivo para o grupo do anúncio; portais
    do mesmo grupo compartilham códigos, então um anúncio visto em um conta para o outro.
    """
    if not pasta.exists():
        return set()
    vistos = set()
    for arquivo in pasta.iterdir():
        if not NOME_ARQUIVO.search(arquivo.name):
            continue
        for site, codigo in LINHA_SITE.findall(arquivo.read_text(encoding="utf-8")):
            if site in grupo_do_site:
                vistos.add((grupo_do_site[site], codigo))
    return vistos
