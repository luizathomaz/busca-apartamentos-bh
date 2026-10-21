from sites import grupo_zap

GRUPO = grupo_zap.GRUPO


def _url_busca(slug):
    return f"https://www.vivareal.com.br/aluguel/minas-gerais/belo-horizonte/bairros/{slug}/apartamento_residencial/"


def buscar(bairros, quartos_min, preco_max, log=print):
    return grupo_zap.buscar("VivaReal", _url_busca, bairros, quartos_min, preco_max, log)
