from sites import grupo_zap

GRUPO = grupo_zap.GRUPO

PORTAL = {
    "nome_api": "VIVAREAL",
    "api_locais": "https://glue-api.vivareal.com/v3/locations",
    "dominio": "vivareal.com.br",
    "base": "https://www.vivareal.com.br",
    "url_busca": lambda caminho: f"https://www.vivareal.com.br{caminho}apartamento_residencial/",
}


def buscar(local, bairros, quartos_min, preco_max, log=print):
    return grupo_zap.buscar("VivaReal", PORTAL, local, bairros, quartos_min, preco_max, log)
