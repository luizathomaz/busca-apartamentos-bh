import json
import re
import time
import unicodedata

from curl_cffi import requests

GRUPO = "quintoandar"
BASE = "https://www.quintoandar.com.br"
API = "https://apigw.prod.quintoandar.com.br/house-listing-search/v2/search/list"
PAUSA = 1.0
POR_PAGINA = 100
# A área que o site calcula para um bairro deixa de fora anúncios das bordas.
FOLGA_GRAUS = 0.01


def _normalizar(texto):
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower().strip()


def _next_data(sessao, url, completo, tentativas=3):
    """Estado da página; `completo` diz se a resposta veio inteira.

    O site às vezes devolve a página com o estado vazio; uma nova tentativa costuma resolver.
    """
    for tentativa in range(tentativas):
        if tentativa:
            time.sleep(PAUSA * 2)
        r = sessao.get(url, timeout=30)
        r.raise_for_status()
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
        if m:
            estado = json.loads(m.group(1))["props"]["pageProps"]["initialState"]
            if completo(estado):
                return estado
    raise RuntimeError(f"página veio incompleta {tentativas} vezes: {url}")


def _area_de_busca(sessao, local, bairros):
    """Retângulo do mapa que cobre todos os bairros, a partir da área que o site usa para cada um."""
    norte, sul, leste, oeste = [], [], [], []
    for nome, slug in bairros.items():
        url = f"{BASE}/alugar/imovel/{slug}-{local.slug_cidade}-{local.slug_uf}-brasil"
        try:
            vp = _next_data(sessao, url, lambda e: ((e.get("search") or {}).get("location") or {}).get("viewport"))["search"]["location"]["viewport"]
        except RuntimeError as e:
            raise RuntimeError(f"não foi possível localizar o bairro {nome} no mapa ({e})")
        norte.append(vp["north"])
        sul.append(vp["south"])
        leste.append(vp["east"])
        oeste.append(vp["west"])
        time.sleep(PAUSA)
    area = {
        "north": max(norte) + FOLGA_GRAUS,
        "south": min(sul) - FOLGA_GRAUS,
        "east": max(leste) + FOLGA_GRAUS,
        "west": min(oeste) - FOLGA_GRAUS,
    }
    centro = {"lat": (area["north"] + area["south"]) / 2, "lng": (area["east"] + area["west"]) / 2}
    return area, centro


def _buscar_pagina(sessao, local, area, centro, quartos_min, preco_max, offset):
    corpo = {
        "context": {"mapShowing": False, "listShowing": True, "numPhotos": 0, "isSSR": False},
        "filters": {
            "businessContext": "RENT",
            "blocklist": [],
            "selectedHouses": [],
            "location": {"coordinate": centro, "viewport": area, "neighborhoods": [],
                         "city": local.cidade, "countryCode": "BR"},
            # Só o aluguel; o condomínio é somado e filtrado depois.
            "priceRange": [{"costType": "RENT_PRICE", "range": {"max": preco_max}}],
            "specialConditions": [],
            "excludedSpecialConditions": [],
            "houseSpecs": {
                "area": {"range": {}}, "houseTypes": ["APARTMENT"], "amenities": [], "installations": [],
                "bathrooms": {"range": {}}, "bedrooms": {"range": {"min": quartos_min}},
                "parkingSpace": {"range": {}}, "suites": {"range": {}},
            },
            "availability": "ANY",
            "occupancy": "ANY",
            "partnerIds": [],
            "categories": [],
            "enableFlexibleSearch": False,
        },
        "sorting": {"criteria": "RELEVANCE", "order": "DESC"},
        "pagination": {"pageSize": POR_PAGINA, "offset": offset},
        "fields": ["id", "neighbourhood", "bedrooms", "rent", "condominium"],
    }
    r = sessao.post(API, json=corpo, timeout=30,
                    headers={"Origin": BASE, "Referer": BASE + "/"})
    r.raise_for_status()
    hits = r.json()["hits"]
    return hits["total"]["value"], [h["_source"] for h in hits["hits"]]


def _data(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else ""


def _anunciado(publicado, primeira):
    if not publicado:
        return "não informado pelo site"
    if primeira and primeira != publicado:
        return f"desde {publicado} (o imóvel apareceu no site pela 1ª vez em {primeira})"
    return f"desde {publicado}"


def _detalhes(sessao, codigo):
    casa = _next_data(
        sessao, f"{BASE}/imovel/{codigo}",
        lambda e: (e.get("house") or {}).get("houseInfo", {}).get("rentPrice"),
    )["house"]["houseInfo"]
    endereco = casa.get("address") or {}
    publicacoes = [l.get("firstPublicationDate") for l in casa.get("listings") or [] if l.get("firstPublicationDate")]
    gerada = (casa.get("generatedDescription") or {}).get("longDescription") or ""
    return {
        # "remarks" é o texto do anunciante; sem ele, o site mostra uma descrição gerada.
        "descricao": casa.get("remarks") or gerada,
        "rua": endereco.get("street") or "",
        "bairro": endereco.get("neighborhood") or "",
        "aluguel": casa.get("rentPrice"),
        "condominio": casa.get("condoPrice"),
        "iptu": casa.get("iptu"),
        "quartos": casa.get("bedrooms"),
        "banheiros": casa.get("bathrooms"),
        "vagas": casa.get("parkingSpaces"),
        "area": f"{casa['area']} m²" if casa.get("area") else "",
        "titulo": (casa.get("generatedDescription") or {}).get("shortRentDescription") or "Apartamento para alugar",
        # O mesmo imóvel volta ao site a cada nova locação; a data do anúncio atual é a última publicação.
        "publicado": _data(casa.get("lastPublishedDate")),
        "primeira_publicacao": _data(min(publicacoes)) if publicacoes else "",
    }


def buscar(local, bairros, quartos_min, preco_max, log=print):
    """Retorna (anúncios que passam no filtro, resumo por bairro)."""
    sessao = requests.Session(impersonate="chrome")
    area, centro = _area_de_busca(sessao, local, bairros)

    vistos, offset = {}, 0
    while True:
        total, itens = _buscar_pagina(sessao, local, area, centro, quartos_min, preco_max, offset)
        vistos.update((str(i["id"]), i) for i in itens)
        offset += POR_PAGINA
        if not itens or offset >= total:
            break
        time.sleep(PAUSA)

    # A busca é por área do mapa e traz bairros vizinhos; fica só o que está na lista.
    nome_por_chave = {_normalizar(n): n for n in bairros}
    por_bairro = {n: [] for n in bairros}
    for codigo, item in vistos.items():
        nome = nome_por_chave.get(_normalizar(item.get("neighbourhood")))
        if nome:
            por_bairro[nome].append(codigo)

    encontrados, resumo = [], {}
    for nome, codigos in por_bairro.items():
        aprovados = 0
        for codigo in codigos:
            item = vistos[codigo]
            if (item.get("bedrooms") or 0) < quartos_min:
                continue
            if (item.get("rent") or 0) + (item.get("condominium") or 0) >= preco_max:
                continue

            try:
                det = _detalhes(sessao, codigo)
            except Exception as e:
                log(f"  anúncio {codigo}: não foi possível ler os detalhes ({e})")
                continue
            time.sleep(PAUSA)
            aluguel = det["aluguel"] if det["aluguel"] is not None else item.get("rent")
            if aluguel is None:
                continue
            condominio = det["condominio"] if det["condominio"] is not None else item.get("condominium")
            total = aluguel + (condominio or 0)
            if total >= preco_max:
                continue

            encontrados.append({
                "site": "QuintoAndar",
                "codigo": codigo,
                "titulo": det["titulo"],
                "bairro": det["bairro"] or nome,
                "cidade": local.cidade,
                "rua": det["rua"],
                "quartos": det["quartos"],
                "banheiros": det["banheiros"],
                "vagas": det["vagas"],
                "area": det["area"],
                "aluguel": float(aluguel),
                "condominio": float(condominio) if condominio is not None else None,
                "iptu": float(det["iptu"]) if det["iptu"] is not None else None,
                "total": float(total),
                "descricao": det["descricao"],
                "anunciado": _anunciado(det["publicado"], det["primeira_publicacao"]),
                "link": f"{BASE}/imovel/{codigo}",
            })
            aprovados += 1
        resumo[nome] = (len(codigos), aprovados)
        log(f"  {nome}: {len(codigos)} apartamentos na busca, {aprovados} dentro do filtro")

    return encontrados, resumo
