"""Raspagem comum ao VivaReal e ao ZAP Imóveis, que usam o mesmo site por baixo."""
import json
import re
import time

from bs4 import BeautifulSoup
from curl_cffi import requests

GRUPO = "grupo_zap"
PAUSA = 1.0
MAX_PAGINAS = 20
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _valor(texto):
    """'R$ 3.200' -> 3200.0; sem número -> None."""
    m = re.search(r"R\$\s*([\d.]+(?:,\d+)?)", texto or "")
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


def _nova_sessao():
    # Os dois portais ficam atrás do Cloudflare, que barra clientes HTTP comuns;
    # o curl_cffi imita a conexão de um Chrome.
    return requests.Session(impersonate="chrome")


def _texto(card, campo):
    el = card.select_one(f'[data-cy="rp-cardProperty-{campo}"]')
    return el.get_text(" ", strip=True) if el else ""


def _inteiro(texto):
    m = re.search(r"\d+", texto)
    return int(m.group()) if m else None


def _ler_pagina(sessao, url, quartos_min, preco_max, pagina):
    params = {
        "quartos": ",".join(str(q) for q in range(quartos_min, 5)),
        # Só o aluguel; o condomínio é somado e filtrado depois.
        "precoMaximo": preco_max,
    }
    if pagina > 1:
        params["pagina"] = pagina
    r = sessao.get(url, params=params, timeout=30)
    r.raise_for_status()
    sopa = BeautifulSoup(r.text, "html.parser")

    # Cards de anunciante agrupam vários imóveis; o card de um imóvel tem um único preço.
    cards = [
        c for c in sopa.select('[data-cy="rp-property-cd"]')
        if len(c.select('[data-cy="rp-cardProperty-price-txt"]')) == 1
    ]
    estruturados = next(
        (json.loads(s.string) for s in sopa.find_all("script", type="application/ld+json")
         if (s.string or "").lstrip().startswith("[")),
        [],
    )
    # Alguns cards não trazem link; o JSON estruturado vem na mesma ordem dos cards.
    if len(estruturados) != len(cards):
        raise RuntimeError(f"página {pagina} de {url}: cards e dados estruturados não batem")

    itens = []
    for card, dados in zip(cards, estruturados):
        preco = _texto(card, "price-txt")
        aluguel_txt, _, resto = preco.partition("/")
        cond = re.search(r"Cond\.\s*(R\$\s*[\d.,]+)", resto)
        iptu = re.search(r"IPTU\s*(R\$\s*[\d.,]+)", resto)
        rua = _texto(card, "street-txt")
        itens.append({
            "codigo": str(dados.get("@id")),
            "link": dados.get("url", "").split("?")[0],
            "titulo": dados.get("name", "").split(" em ")[0],
            "bairro": _texto(card, "location-txt").split(",")[0].strip(),
            "rua": "" if "não informado" in rua.lower() else rua,
            "quartos": _inteiro(_texto(card, "bedroomQuantity-txt")),
            "banheiros": _inteiro(_texto(card, "bathroomQuantity-txt")),
            "vagas": _inteiro(_texto(card, "parkingSpacesQuantity-txt")),
            "area": _texto(card, "propertyArea-txt").replace("Tamanho do imóvel", "").strip(),
            "aluguel": _valor(aluguel_txt),
            "condominio": _valor(cond.group(1)) if cond else None,
            "iptu": _valor(iptu.group(1)) if iptu else None,
        })
    return itens


def _detalhes(sessao, link):
    r = sessao.get(link, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    sopa = BeautifulSoup(r.text, "html.parser")
    descricao = sopa.select_one('[data-testid="description-content"]')
    endereco = sopa.select_one('[data-testid="location-address"]')
    criacao = sopa.select_one('[data-testid="listing-created-date"]')
    return (
        descricao.get_text("\n", strip=True) if descricao else "",
        # Anunciantes que escondem o número publicam "000".
        re.sub(r",\s*0+(?=\s|$)", "", endereco.get_text(" ", strip=True)) if endereco else "",
        _data_criacao(criacao.get_text(" ", strip=True) if criacao else ""),
    )


def _data_criacao(texto):
    """'Anúncio criado em 14 de outubro de 2026 , atualizado há 6 dias .' -> '14/10/2026 (atualizado há 6 dias)'."""
    m = re.search(r"(\d{1,2}) de (\w+) de (\d{4})", texto)
    if not m or m.group(2).lower() not in MESES:
        return ""
    data = f"{int(m.group(1)):02d}/{MESES.index(m.group(2).lower()) + 1:02d}/{m.group(3)}"
    atualizado = re.search(r"atualizado [^.,]+", texto)
    return f"{data} ({atualizado.group().strip()})" if atualizado else data


def buscar(site, url_busca, bairros, quartos_min, preco_max, log=print):
    """Retorna (anúncios que passam no filtro, resumo por bairro)."""
    sessao = _nova_sessao()
    nomes_aceitos = set(bairros)
    encontrados, vistos_global, resumo = [], set(), {}

    for nome, slug in bairros.items():
        vistos, pagina = {}, 1
        try:
            while pagina <= MAX_PAGINAS:
                novos = [i for i in _ler_pagina(sessao, url_busca(slug), quartos_min, preco_max, pagina)
                         if i["codigo"] not in vistos]
                if not novos:
                    break
                vistos.update((i["codigo"], i) for i in novos)
                pagina += 1
                time.sleep(PAUSA)
        except Exception as e:
            # Um bairro com endereço errado no site não derruba a busca dos outros.
            resumo[nome] = (f"FALHOU ({e})", 0)
            log(f"  {nome}: falhou ({e})")
            continue

        aprovados = 0
        for item in vistos.values():
            # A busca por bairro também traz vizinhos (ex.: Funcionários na Savassi).
            if item["bairro"] not in nomes_aceitos or item["codigo"] in vistos_global:
                continue
            if (item["quartos"] or 0) < quartos_min or item["aluguel"] is None:
                continue
            total = item["aluguel"] + (item["condominio"] or 0)
            if total >= preco_max:
                continue

            try:
                detalhes = _detalhes(sessao, item["link"])
            except Exception as e:
                detalhes = (f"(não foi possível ler a descrição: {e})", "", "")
            time.sleep(PAUSA)
            # A busca ainda lista anúncios já retirados do ar.
            if detalhes is None:
                continue
            descricao, endereco, criado_em = detalhes

            vistos_global.add(item["codigo"])
            encontrados.append({
                **item,
                "site": site,
                "cidade": "Belo Horizonte",
                "endereco": endereco,
                "anunciado": f"desde {criado_em}" if criado_em else "não informado pelo site",
                "total": total,
                "descricao": descricao,
            })
            aprovados += 1

        resumo[nome] = (len(vistos), aprovados)
        log(f"  {nome}: {len(vistos)} apartamentos na busca, {aprovados} dentro do filtro")
        time.sleep(PAUSA)

    return encontrados, resumo
