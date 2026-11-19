"""Parâmetros da busca. Edite este arquivo e rode buscar_apartamentos.py de novo.

Escreva os nomes como aparecem nos sites, com acento. Os endereços das buscas são
montados a partir deles (ex.: "São Bento" vira "sao-bento").
"""

CIDADE = "Belo Horizonte"
ESTADO = "Minas Gerais"
UF = "MG"

BAIRROS = [
    "São Bento",
    "Santo Antônio",
    "São Pedro",
    "Savassi",
    "Sion",
    "Anchieta",
    "Carmo",
    "Cruzeiro",
    "Vila Paris",
    "Lourdes",
    "Funcionários",
    "Cidade Jardim",
]

QUARTOS_MIN = 2

# Aluguel + condomínio, estritamente abaixo deste valor. O IPTU não entra na conta.
PRECO_MAX = 3500

# Apague da lista os sites que não quiser usar. O Netimóveis atende sobretudo Minas Gerais.
SITES = ["Netimóveis", "VivaReal", "ZAP Imóveis", "QuintoAndar"]
