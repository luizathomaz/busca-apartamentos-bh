# Busca de apartamentos

Procura apartamentos para alugar no Netimóveis, VivaReal, ZAP Imóveis e QuintoAndar, nos
bairros e com os filtros que você escolher, e salva cada rodada num arquivo de texto em
`resultados/`. Cada anúncio aparece uma vez só: nas rodadas seguintes, só vêm os novos.

## 1. Baixar

O repositório é privado. Peça acesso a quem o mantém e baixe de um destes jeitos:

- **Sem git:** no GitHub, clique em **Code → Download ZIP** e descompacte a pasta.
- **Com git:** `git clone https://github.com/luizathomaz/busca-apartamentos-bh.git`

## 2. Instalar (só na primeira vez)

Precisa do Python 3.10 ou mais novo. Para conferir, abra o Terminal (Mac) ou o Prompt de
Comando (Windows) e rode `python3 --version` (no Windows, `py --version`). Se não tiver,
baixe em [python.org/downloads](https://www.python.org/downloads/); no Windows, marque
**Add Python to PATH** durante a instalação.

No terminal, entre na pasta do projeto (`cd` seguido do caminho da pasta) e rode:

**Mac / Linux**

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**Windows**

```
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## 3. Escolher cidade, bairros e filtros

Abra o arquivo `config.py` num editor de texto (Bloco de Notas, TextEdit, VS Code) e troque
os valores:

```python
CIDADE = "São Paulo"
ESTADO = "São Paulo"
UF = "SP"

BAIRROS = [
    "Pinheiros",
    "Vila Madalena",
    "Santa Cecília",
]

QUARTOS_MIN = 2
PRECO_MAX = 4000

SITES = ["Netimóveis", "VivaReal", "ZAP Imóveis", "QuintoAndar"]
```

| Campo | O que é |
|---|---|
| `CIDADE`, `ESTADO`, `UF` | Nome da cidade, nome do estado por extenso e a sigla do estado. |
| `BAIRROS` | Os bairros, um por linha, entre aspas e com vírgula no fim. |
| `QUARTOS_MIN` | Número mínimo de quartos. |
| `PRECO_MAX` | Teto de aluguel + condomínio (o anúncio precisa ficar abaixo dele). O IPTU não entra. |
| `SITES` | Os sites usados. Apague os que não quiser, mas mantenha a grafia dos que ficarem. |

Escreva os nomes como aparecem nos sites, com acento e maiúsculas: `"Santa Cecília"`, não
`"sta cecilia"`.

## 4. Rodar

**Mac / Linux**

```
.venv/bin/python buscar_apartamentos.py
```

**Windows**

```
.venv\Scripts\python buscar_apartamentos.py
```

A busca leva alguns minutos, porque abre cada anúncio para ler a descrição. No fim, o
terminal mostra o arquivo gerado, por exemplo `resultados/rodada_2026-11-19_14h30.txt`, com
os anúncios ordenados do mais barato para o mais caro.

## Dúvidas comuns

- **"bairro não encontrado no site"**: o VivaReal ou o ZAP não reconheceram o nome. Busque o
  bairro no próprio site e copie o nome do jeito que ele aparece lá.
- **Um site falhou ou trouxe 0 anúncios**: os outros seguem normalmente. O Netimóveis tem
  poucos anúncios fora de Minas Gerais; se não fizer sentido para sua cidade, tire-o de
  `SITES`.
- **Quero ver de novo anúncios que já apareceram**: o programa lê as rodadas antigas para
  saber o que já mostrou. Apague (ou mova) os arquivos de `resultados/` e rode de novo.
- **Mudei de cidade**: pode manter os arquivos antigos; anúncios de outra cidade não atrapalham.
