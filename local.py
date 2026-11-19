"""Cidade da busca e os nomes no formato que os sites usam nas URLs."""
import re
import unicodedata
from dataclasses import dataclass


def slug(texto):
    """'São Bento' -> 'sao-bento'."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


@dataclass(frozen=True)
class Local:
    cidade: str
    estado: str
    uf: str

    @property
    def slug_cidade(self):
        return slug(self.cidade)

    @property
    def slug_estado(self):
        return slug(self.estado)

    @property
    def slug_uf(self):
        return slug(self.uf)
