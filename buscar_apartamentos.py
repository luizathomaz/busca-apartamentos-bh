"""Busca apartamentos para alugar em Belo Horizonte e salva o resultado em resultados/."""
import textwrap
from datetime import datetime
from pathlib import Path

import historico
from sites import netimoveis, quintoandar, vivareal, zapimoveis

QUARTOS_MIN = 2
PRECO_MAX = 3500  # aluguel + condomínio, estritamente abaixo

BAIRROS = {
    "São Bento": "sao-bento",
    "Santo Antônio": "santo-antonio",
    "São Pedro": "sao-pedro",
    "Savassi": "savassi",
    "Sion": "sion",
    "Anchieta": "anchieta",
    "Carmo": "carmo",
    "Cruzeiro": "cruzeiro",
    "Vila Paris": "vila-paris",
    "Lourdes": "lourdes",
    "Funcionários": "funcionarios",
    "Cidade Jardim": "cidade-jardim",
}

# Portais do mesmo grupo compartilham anúncios: um anúncio já listado num site
# anterior desta lista não se repete no seguinte.
SITES = {
    "Netimóveis": netimoveis,
    "VivaReal": vivareal,
    "ZAP Imóveis": zapimoveis,
    "QuintoAndar": quintoandar,
}

PASTA_RESULTADOS = Path(__file__).parent / "resultados"


def reais(v):
    if v is None:
        return "não informado"
    inteiro, _, centavos = f"{v:,.2f}".partition(".")
    texto = "R$ " + inteiro.replace(",", ".")
    return texto if centavos == "00" else f"{texto},{centavos}"


def formatar(ap, n):
    local = ap.get("endereco") or ", ".join(p for p in (ap["rua"], ap["bairro"], ap["cidade"]) if p)
    condominio = reais(ap["condominio"])
    if ap["condominio"] is None:
        condominio += " (confirme com o anunciante; total considera R$ 0)"
    descricao = "\n".join(
        textwrap.fill(par, width=90, initial_indent="    ", subsequent_indent="    ")
        for par in ap["descricao"].splitlines() if par.strip()
    ) or "    (sem descrição no anúncio)"

    return "\n".join([
        f"[{n}] {ap['titulo']}",
        f"Site:        {ap['site']} (código {ap['codigo']})",
        f"Anunciado:   {ap['anunciado']}",
        f"Localização: {local}",
        f"Quartos: {ap['quartos']} | Banheiros: {ap['banheiros'] or 'não informado'} | "
        f"Vagas: {ap['vagas'] or 0} | Área: {ap['area'] or 'não informada'}",
        f"Aluguel:     {reais(ap['aluguel'])}",
        f"Condomínio:  {condominio}",
        f"TOTAL:       {reais(ap['total'])} /mês",
        f"IPTU:        {reais(ap['iptu'])} (não entra no total)",
        f"Link:        {ap['link']}",
        "Descrição:",
        descricao,
    ])


def classificar(aps, grupo, vistos, mostrados_nesta_rodada):
    """Separa os anúncios que nunca apareceram dos que já saíram numa rodada anterior.

    Retorna (a mostrar, quantos já vistos antes, quantos já listados por outro site nesta rodada).
    """
    mostrar, ja_vistos, de_outro_site = [], 0, 0
    for ap in aps:
        chave = (grupo, ap["codigo"])
        if chave in mostrados_nesta_rodada:
            de_outro_site += 1
            continue
        mostrados_nesta_rodada.add(chave)
        # Mesmo que preço ou descrição tenham mudado, o anúncio não volta.
        if chave in vistos:
            ja_vistos += 1
            continue
        mostrar.append(ap)
    return mostrar, ja_vistos, de_outro_site


def secao(r):
    linhas = [
        "#" * 90,
        f"#  {r['nome'].upper()}",
        "#" * 90,
        "",
    ]
    if r["erro"]:
        return linhas + [f"Busca falhou neste site: {r['erro']}", ""]

    no_filtro = len(r["mostrar"]) + r["ja_vistos"] + r["de_outro_site"]
    linhas += [
        f"Dentro do filtro: {no_filtro}",
        f"  - Novos (listados abaixo): {len(r['mostrar'])}",
        f"  - Já vistos em rodadas anteriores (omitidos): {r['ja_vistos']}",
    ]
    if r["de_outro_site"]:
        linhas.append(f"  - Já listados em outro site do mesmo grupo nesta rodada (omitidos): {r['de_outro_site']}")
    linhas += ["", "Por bairro (anúncios na busca -> dentro do filtro):"]
    linhas += [f"  - {b}: {vistos} -> {ok}" for b, (vistos, ok) in r["resumo"].items()]
    linhas.append("")
    if not r["mostrar"]:
        linhas += ["Nenhum anúncio novo neste site.", ""]
    for n, ap in enumerate(sorted(r["mostrar"], key=lambda a: a["total"]), 1):
        linhas += ["-" * 90, formatar(ap, n), ""]
    return linhas


def main():
    inicio = datetime.now()
    vistos = historico.carregar(PASTA_RESULTADOS, {nome: m.GRUPO for nome, m in SITES.items()})
    mostrados = set()
    resultados = []
    for nome, modulo in SITES.items():
        print(f"Buscando no {nome} ({len(BAIRROS)} bairros)...")
        r = {"nome": nome, "mostrar": [], "ja_vistos": 0, "de_outro_site": 0, "resumo": {}, "erro": None}
        try:
            aps, r["resumo"] = modulo.buscar(BAIRROS, QUARTOS_MIN, PRECO_MAX)
            r["mostrar"], r["ja_vistos"], r["de_outro_site"] = classificar(aps, modulo.GRUPO, vistos, mostrados)
        except Exception as e:
            print(f"  falhou: {e}")
            r["erro"] = e
        resultados.append(r)

    separador = "=" * 90
    linhas = [
        separador,
        "PESQUISA DE APARTAMENTOS PARA ALUGAR - BELO HORIZONTE",
        f"Rodada:  {inicio:%d/%m/%Y %H:%M}",
        f"Filtros: {QUARTOS_MIN}+ quartos | aluguel + condomínio abaixo de {reais(PRECO_MAX)}",
        f"Bairros: {', '.join(BAIRROS)}",
        "Só aparecem anúncios que não saíram em nenhuma rodada anterior.",
        separador,
        "",
        "Resumo (novos):",
    ]
    for r in resultados:
        linhas.append(f"  - {r['nome']}: {'FALHOU' if r['erro'] else len(r['mostrar'])}")
    linhas.append("")
    for r in resultados:
        linhas += secao(r)

    PASTA_RESULTADOS.mkdir(exist_ok=True)
    arquivo = PASTA_RESULTADOS / f"rodada_{inicio:%Y-%m-%d_%Hh%M}.txt"
    arquivo.write_text("\n".join(linhas), encoding="utf-8")
    total = sum(len(r["mostrar"]) for r in resultados)
    print(f"\n{total} apartamento(s) novos. Resultado salvo em {arquivo}")


if __name__ == "__main__":
    main()
