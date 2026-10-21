# Busca de apartamentos

Procura apartamentos para alugar em Belo Horizonte no Netimóveis, VivaReal e ZAP Imóveis
e salva cada rodada em `resultados/rodada_AAAA-MM-DD_HHhMM.txt`.

Filtros (no topo de `buscar_apartamentos.py`): 2+ quartos, aluguel + condomínio abaixo de
R$ 3.500 e a lista de bairros. Anúncios que já apareceram em rodadas anteriores só voltam
se mudarem.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python buscar_apartamentos.py
```
