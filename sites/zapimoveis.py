from sites import grupo_zap

GRUPO = grupo_zap.GRUPO

PORTAL = {
    "nome_api": "ZAP",
    "api_locais": "https://glue-api.zapimoveis.com.br/v3/locations",
    "dominio": "zapimoveis.com.br",
    "base": "https://www.zapimoveis.com.br",
    # O autocompletar devolve a busca de todos os imóveis; a listagem só de apartamentos troca o tipo.
    "url_busca": lambda caminho: "https://www.zapimoveis.com.br"
                                 + caminho.replace("/aluguel/imoveis/", "/aluguel/apartamentos/", 1),
}


def buscar(local, bairros, quartos_min, preco_max, log=print):
    return grupo_zap.buscar("ZAP Imóveis", PORTAL, local, bairros, quartos_min, preco_max, log)
