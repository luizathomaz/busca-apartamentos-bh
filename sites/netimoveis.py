import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

GRUPO = "netimoveis"
BASE = "https://www.netimoveis.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
POR_PAGINA = 21
PAUSA = 0.5


def _valor(texto):
    """'R$ 3.100' -> 3100.0; vazio ou 'Consulte' -> None."""
    if not texto:
        return None
    digitos = re.sub(r"[^\d,]", "", texto).replace(",", ".")
    return float(digitos) if digitos else None


def _nova_sessao():
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    # A API só responde depois que a sessão tem os cookies da página de listagem.
    s.get(f"{BASE}/locacao/minas-gerais/belo-horizonte/apartamento", timeout=30)
    return s


def _buscar_pagina(sessao, slug_bairro, pagina):
    corpo = {
        "registrosPorPagina": POR_PAGINA,
        "timestampBusca": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "modoBusca": "csr",
        "pagina": pagina,
        "transacao": "locacao",
        "tipos": ["apartamento"],
        "caracteristicas": [],
        "localizacao": {
            "urlEstado": "minas-gerais",
            "urlCidade": "belo-horizonte",
            # O site exige uma região na URL, mas filtra só pelo bairro.
            "urlRegiao": slug_bairro,
            "urlBairro": slug_bairro,
            "urlLogradouro": "",
            "urlTipoLocalizacao": "Bairro",
        },
        "order": "maior-pontuacao",
        "formato": "lista",
        "coordenadas": [],
        "imovel": [],
    }
    r = sessao.post(f"{BASE}/Listagem/Buscar", json=corpo, timeout=30)
    if r.status_code == 422:
        return 0, []
    r.raise_for_status()
    dados = r.json()
    if dados.get("erro"):
        raise RuntimeError(dados.get("mensagem") or "erro na API do Netimóveis")
    return dados.get("quantidadeTotalImoveis") or 0, dados.get("imovelCampos") or []


def _detalhes(sessao, link):
    r = sessao.get(link, timeout=30)
    r.raise_for_status()
    sopa = BeautifulSoup(r.text, "html.parser")
    corpo = sopa.select_one("#detalhe-descricao .pn-d-s02-body")
    if corpo:
        descricao = corpo.get_text("\n", strip=True)
    else:
        meta = sopa.find("meta", attrs={"name": "description"})
        descricao = meta["content"].strip() if meta and meta.get("content") else ""
    # O site não publica a data de criação do anúncio, só a da última alteração.
    m = re.search(r'"dateModified"\s*:\s*"(\d{4})-(\d{2})-(\d{2})', r.text)
    atualizado = f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else ""
    return descricao, atualizado


def buscar(bairros, quartos_min, preco_max, log=print):
    """Retorna (anúncios que passam no filtro, resumo por bairro)."""
    sessao = _nova_sessao()
    encontrados, codigos, resumo = [], set(), {}

    for nome, slug in bairros.items():
        vistos, pagina, total = [], 1, None
        while True:
            total, itens = _buscar_pagina(sessao, slug, pagina)
            vistos.extend(itens)
            if not itens or len(vistos) >= total:
                break
            pagina += 1
            time.sleep(PAUSA)

        aprovados = 0
        for item in vistos:
            # O mesmo anúncio pode aparecer na busca de mais de um bairro.
            if item.get("imovel_id") in codigos:
                continue
            if (item.get("quartos") or 0) < quartos_min:
                continue
            aluguel = _valor(item.get("valorImovel"))
            if aluguel is None:
                continue
            condominio = _valor(item.get("valorCondominio"))
            total_mensal = aluguel + (condominio or 0)
            if total_mensal >= preco_max:
                continue

            link = BASE + item["link"].split("?")[0]
            try:
                descricao, atualizado = _detalhes(sessao, link)
            except requests.RequestException as e:
                descricao, atualizado = f"(não foi possível ler a descrição: {e})", ""
            time.sleep(PAUSA)

            codigos.add(item.get("imovel_id"))
            encontrados.append({
                "site": "Netimóveis",
                "codigo": item.get("imovel_id"),
                "titulo": item.get("titulo") or "",
                "bairro": item.get("bairro") or nome,
                "cidade": item.get("cidade") or "Belo Horizonte",
                "rua": item.get("logradouro") or "",
                "quartos": item.get("quartos"),
                "banheiros": item.get("banhos"),
                "vagas": item.get("vagasGaragem"),
                "area": item.get("areaRealPrivativa") or "",
                "aluguel": aluguel,
                "condominio": condominio,
                "iptu": _valor(item.get("valorIptu")),
                "total": total_mensal,
                "descricao": descricao,
                "anunciado": "não informado pelo site"
                             + (f" (última atualização em {atualizado})" if atualizado else ""),
                "link": link,
            })
            aprovados += 1

        resumo[nome] = (len(vistos), aprovados)
        log(f"  {nome}: {len(vistos)} apartamentos no site, {aprovados} dentro do filtro")
        time.sleep(PAUSA)

    return encontrados, resumo
