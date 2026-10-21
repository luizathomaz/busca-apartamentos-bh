"""Lê as rodadas anteriores em resultados/ para saber quais anúncios já foram mostrados."""
import re
from datetime import datetime

SEPARADOR_ANUNCIO = "-" * 90
NOME_ARQUIVO = re.compile(r"rodada_(\d{4}-\d{2}-\d{2}_\d{2}h\d{2})\.txt$")


def campos_rastreados(aluguel, condominio, iptu, imovel, descricao):
    """Campos cuja mudança faz um anúncio já visto aparecer de novo, como texto."""
    return {
        "aluguel": aluguel,
        "condomínio": condominio,
        "IPTU": iptu,
        "imóvel": imovel,
        # A descrição é quebrada em linhas no arquivo; compara sem espaços.
        "descrição": re.sub(r"\s+", "", descricao),
    }


def _valor_linha(bloco, rotulo):
    m = re.search(rf"^{rotulo}:\s*(.*)$", bloco, re.M)
    # Tira observações entre parênteses, como "(não entra no total)".
    return m.group(1).split(" (")[0].strip() if m else ""


def _ler_bloco(bloco):
    site = re.search(r"^Site:\s+(.+?) \(código (\S+)\)", bloco, re.M)
    if not site:
        return None
    imovel = re.search(r"^(Quartos: .*)$", bloco, re.M)
    descricao = bloco.split("Descrição:", 1)[1] if "Descrição:" in bloco else ""
    if descricao.strip() == "(sem descrição no anúncio)":
        descricao = ""
    return site.group(1), site.group(2), campos_rastreados(
        _valor_linha(bloco, "Aluguel"),
        _valor_linha(bloco, "Condomínio"),
        _valor_linha(bloco, "IPTU"),
        imovel.group(1).strip() if imovel else "",
        descricao,
    )


def carregar(pasta, grupo_do_site):
    """Retorna {(grupo, código): {"primeira_vez", "ultima_vez", "campos"}} das rodadas em `pasta`.

    `grupo_do_site` mapeia o nome do site no arquivo para o grupo do anúncio; portais
    do mesmo grupo compartilham códigos, então um anúncio visto em um conta para o outro.
    """
    historico = {}
    if not pasta.exists():
        return historico
    arquivos = sorted(
        (datetime.strptime(m.group(1), "%Y-%m-%d_%Hh%M"), p)
        for p in pasta.iterdir() if (m := NOME_ARQUIVO.search(p.name))
    )
    for quando, arquivo in arquivos:
        for bloco in arquivo.read_text(encoding="utf-8").split(SEPARADOR_ANUNCIO)[1:]:
            # O último anúncio de uma seção vem colado ao cabeçalho da seção seguinte.
            lido = _ler_bloco(bloco.split("#" * 90)[0])
            if not lido or lido[0] not in grupo_do_site:
                continue
            site, codigo, campos = lido
            chave = (grupo_do_site[site], codigo)
            anterior = historico.get(chave)
            historico[chave] = {
                "primeira_vez": anterior["primeira_vez"] if anterior else quando,
                "ultima_vez": quando,
                "campos": campos,
            }
    return historico


def mudancas(antes, agora):
    """Lista legível do que mudou entre dois conjuntos de campos rastreados."""
    saida = []
    for campo, valor in agora.items():
        if antes.get(campo) == valor:
            continue
        if campo == "descrição":
            saida.append("descrição")
        else:
            saida.append(f"{campo}: {antes.get(campo) or 'não informado'} -> {valor}")
    return saida
