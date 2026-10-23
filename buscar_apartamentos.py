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


def linha_imovel(ap):
    return (f"Quartos: {ap['quartos']} | Banheiros: {ap['banheiros'] or 'não informado'} | "
            f"Vagas: {ap['vagas'] or 0} | Área: {ap['area'] or 'não informada'}")


def campos(ap):
    return historico.campos_rastreados(
        reais(ap["aluguel"]), reais(ap["condominio"]), reais(ap["iptu"]),
        linha_imovel(ap), ap["descricao"],
    )


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
        f"Status:      {ap['status']}",
        f"Site:        {ap['site']} (código {ap['codigo']})",
        f"Anunciado:   {ap['anunciado']}",
        f"Localização: {local}",
        linha_imovel(ap),
        f"Aluguel:     {reais(ap['aluguel'])}",
        f"Condomínio:  {condominio}",
        f"TOTAL:       {reais(ap['total'])} /mês",
        f"IPTU:        {reais(ap['iptu'])} (não entra no total)",
        f"Link:        {ap['link']}",
        "Descrição:",
        descricao,
    ])


def classificar(aps, grupo, hist, mostrados_nesta_rodada):
    """Separa os anúncios novos ou alterados dos que já apareceram.

    Retorna (a mostrar, quantos já vistos sem mudança, quantos já listados por outro site nesta rodada).
    """
    mostrar, sem_mudanca, de_outro_site = [], 0, 0
    for ap in aps:
        chave = (grupo, ap["codigo"])
        if chave in mostrados_nesta_rodada:
            de_outro_site += 1
            continue
        mostrados_nesta_rodada.add(chave)

        anterior = hist.get(chave)
        if anterior is None:
            ap["status"] = "NOVO"
        else:
            mudou = historico.mudancas(anterior["campos"], campos(ap))
            if not mudou:
                sem_mudanca += 1
                continue
            ap["status"] = (
                f"MUDOU desde a rodada de {anterior['ultima_vez']:%d/%m/%Y %H:%M} "
                f"(visto pela 1ª vez em {anterior['primeira_vez']:%d/%m/%Y}) - " + "; ".join(mudou)
            )
        mostrar.append(ap)
    return mostrar, sem_mudanca, de_outro_site


def secao(r):
    linhas = [
        "#" * 90,
        f"#  {r['nome'].upper()}",
        "#" * 90,
        "",
    ]
    if r["erro"]:
        return linhas + [f"Busca falhou neste site: {r['erro']}", ""]

    no_filtro = len(r["mostrar"]) + r["sem_mudanca"] + r["de_outro_site"]
    linhas += [
        f"Dentro do filtro: {no_filtro}",
        f"  - Novos ou alterados (listados abaixo): {len(r['mostrar'])}",
        f"  - Já vistos em rodadas anteriores, sem mudança (omitidos): {r['sem_mudanca']}",
    ]
    if r["de_outro_site"]:
        linhas.append(f"  - Já listados em outro site do mesmo grupo nesta rodada (omitidos): {r['de_outro_site']}")
    linhas += ["", "Por bairro (anúncios na busca -> dentro do filtro):"]
    linhas += [f"  - {b}: {vistos} -> {ok}" for b, (vistos, ok) in r["resumo"].items()]
    linhas.append("")
    if not r["mostrar"]:
        linhas += ["Nenhum anúncio novo ou alterado neste site.", ""]
    for n, ap in enumerate(sorted(r["mostrar"], key=lambda a: a["total"]), 1):
        linhas += ["-" * 90, formatar(ap, n), ""]
    return linhas


def main():
    inicio = datetime.now()
    hist = historico.carregar(PASTA_RESULTADOS, {nome: m.GRUPO for nome, m in SITES.items()})
    mostrados = set()
    resultados = []
    for nome, modulo in SITES.items():
        print(f"Buscando no {nome} ({len(BAIRROS)} bairros)...")
        r = {"nome": nome, "mostrar": [], "sem_mudanca": 0, "de_outro_site": 0, "resumo": {}, "erro": None}
        try:
            aps, r["resumo"] = modulo.buscar(BAIRROS, QUARTOS_MIN, PRECO_MAX)
            r["mostrar"], r["sem_mudanca"], r["de_outro_site"] = classificar(aps, modulo.GRUPO, hist, mostrados)
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
        "Só aparecem anúncios novos ou que mudaram desde as rodadas anteriores.",
        separador,
        "",
        "Resumo (novos ou alterados):",
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
    print(f"\n{total} apartamento(s) novos ou alterados. Resultado salvo em {arquivo}")


if __name__ == "__main__":
    main()
