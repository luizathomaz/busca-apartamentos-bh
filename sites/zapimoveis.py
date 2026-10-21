from sites import grupo_zap

GRUPO = grupo_zap.GRUPO

# O ZAP abrevia alguns nomes de bairro na URL.
SLUGS_ABREVIADOS = {
    "sao-bento": "s-bento",
    "sao-pedro": "s-pedro",
    "santo-antonio": "sto-antonio",
    "vila-paris": "vl-paris",
}


def _url_busca(slug):
    slug = SLUGS_ABREVIADOS.get(slug, slug)
    return f"https://www.zapimoveis.com.br/aluguel/apartamentos/mg+belo-horizonte++{slug}/"


def buscar(bairros, quartos_min, preco_max, log=print):
    return grupo_zap.buscar("ZAP Imóveis", _url_busca, bairros, quartos_min, preco_max, log)
