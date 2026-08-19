"""Importa a bateria publicada de suplementos concentrados como referência."""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from formulacao.models import (
    ReferenciaSuplementoIngrediente,
    ReferenciaSuplementoValidada,
)


ARQUIVO_FORMULACOES = "formulacoes_ovinocerto_testes.csv"
ARQUIVO_NRC = "exigencias_nutricionais_nrc.csv"
ARQUIVO_INGREDIENTES = "ingredientes_composicao_valadares.csv"
COLUNAS_INGREDIENTES = (
    "trigo_farelo", "milho_grao", "soja_farelo", "calcario_calcitico",
    "sorgo_grao", "milho_germen_farelo", "aveia_grao", "mandioca_farinha",
    "melaco", "bicarbonato_sodio", "cloreto_amonio",
)


def _normalizar(valor: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode()
    return "".join(caractere for caractere in sem_acento.lower() if caractere.isalnum())


def _chave_ingrediente(valor: str) -> str:
    """Normaliza conectivos sem transformar a chave em identificação de catálogo."""
    return _normalizar(" ".join(parte for parte in valor.split() if parte.lower() != "de"))


def _ler_csv(caminho: Path) -> list[dict[str, str]]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


class Command(BaseCommand):
    help = (
        "Importa as formulações publicadas como referências versionadas de "
        "suplemento concentrado. Não altera ingredientes nem exigências NRC."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--diretorio",
            type=Path,
            default=Path(r"C:\\Users\\anaju\\Downloads"),
            help="Pasta que contém os três CSVs validados.",
        )
        parser.add_argument("--versao", default="livro-116-v1")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        diretorio: Path = options["diretorio"]
        caminhos = {
            "formulações": diretorio / ARQUIVO_FORMULACOES,
            "NRC": diretorio / ARQUIVO_NRC,
            "ingredientes": diretorio / ARQUIVO_INGREDIENTES,
        }
        ausentes = [descricao for descricao, caminho in caminhos.items() if not caminho.is_file()]
        if ausentes:
            raise CommandError(f"CSV ausente: {', '.join(ausentes)} em {diretorio}")

        formulacoes = _ler_csv(caminhos["formulações"])
        nrc_por_id = {linha["categoria_id"]: linha for linha in _ler_csv(caminhos["NRC"])}
        ingredientes_por_nome = {
            _chave_ingrediente(linha["ingrediente"]): linha
            for linha in _ler_csv(caminhos["ingredientes"])
        }
        if len(formulacoes) != 116:
            raise CommandError(f"Esperadas 116 formulações; recebidas {len(formulacoes)}.")

        registros = [
            self._validar_e_montar(linha, nrc_por_id, ingredientes_por_nome)
            for linha in formulacoes
        ]
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(
                f"Validação concluída: {len(registros)} referências prontas para importação."
            ))
            return

        with transaction.atomic():
            for referencia, componentes in registros:
                objeto, _ = ReferenciaSuplementoValidada.objects.update_or_create(
                    codigo=referencia.pop("codigo"),
                    defaults={
                        **referencia,
                        "versao_fonte": options["versao"],
                        "origem_arquivo": ARQUIVO_FORMULACOES,
                    },
                )
                # Substitui somente os componentes desta referência, tornando
                # a importação idempotente e preservando qualquer outra fonte.
                objeto.ingredientes.all().delete()
                ReferenciaSuplementoIngrediente.objects.bulk_create([
                    ReferenciaSuplementoIngrediente(referencia=objeto, **componente)
                    for componente in componentes
                ])

        self.stdout.write(self.style.SUCCESS(
            f"{len(registros)} referências importadas/atualizadas na versão {options['versao']}."
        ))

    @staticmethod
    def _validar_e_montar(linha, nrc_por_id, ingredientes_por_nome):
        try:
            nrc = nrc_por_id[linha["categoria_id"]]
        except KeyError as erro:
            raise CommandError(f"NRC inexistente para {linha['categoria_id']}.") from erro

        componentes = []
        soma = 0.0
        for codigo in COLUNAS_INGREDIENTES:
            participacao = float(linha[f"{codigo}_pct_ms"])
            if participacao <= 0.0:
                continue
            ingrediente = ingredientes_por_nome.get(_chave_ingrediente(codigo.replace("_", " ")))
            if ingrediente is None:
                raise CommandError(
                    f"Composição não encontrada para '{codigo}' na formulação "
                    f"{linha['num_formulacao']}."
                )
            componentes.append({
                "codigo_origem": codigo,
                "nome_origem": ingrediente["ingrediente"],
                "classificacao": ingrediente["classificacao"].upper(),
                "tipo": _normalizar(ingrediente["tipo"]).upper(),
                "participacao_pct_ms": participacao,
                "ms_pct": float(ingrediente["ms_pct"]),
                "pb_pct": float(ingrediente["pb_pct"]),
                "ndt_pct": float(ingrediente["ndt_pct"]),
                "fdn_pct": float(ingrediente["fdn_pct"]),
                "ee_pct": float(ingrediente["ee_pct"]),
                "ca_pct": float(ingrediente["ca_pct"]),
                "p_pct": float(ingrediente["p_pct"]),
            })
            soma += participacao
        # A fonte traz participações arredondadas a quatro casas; aceita-se
        # apenas a discrepância máxima observável nessa publicação. A receita
        # persistida não é normalizada, para manter rastreabilidade literal.
        if abs(soma - 100.0) > 0.02:
            raise CommandError(
                f"Formulação {linha['num_formulacao']} não fecha 100% (soma={soma:.4f}%)."
            )

        fase_meses = int(float(linha["fase_meses"]))
        referencia = {
            "codigo": f"LIVRO-{int(linha['num_formulacao']):03d}",
            "fonte": "Bateria publicada de suplementos concentrados",
            "categoria_id_origem": linha["categoria_id"],
            "categoria": f"cordeiros_{fase_meses}_meses",
            "fase": "crescimento",
            "fase_meses": fase_meses,
            "peso_vivo_kg": float(linha["peso_vivo_kg"]),
            "gmd_kg": float(linha["gmd_kg"]),
            "cms_kg": float(nrc["cms_kg"]),
            "pb_requisito_pct": float(nrc["pb_pct"]),
            "ndt_requisito_pct": float(nrc["ndt_pct"]),
            "ca_requisito_pct": float(nrc["ca_pct"]),
            "p_requisito_pct": float(nrc["p_pct"]),
            "ca_p_requisito": float(nrc["ca_p_ratio"]),
            "pb_resultado_pct": float(linha["pb_pct"]),
            "ndt_resultado_pct": float(linha["ndt_pct"]),
            "fdn_resultado_pct": float(linha["fdn_pct"]),
            "ee_resultado_pct": float(linha["ee_pct"]),
            "ca_resultado_pct": float(linha["ca_pct"]),
            "p_resultado_pct": float(linha["p_pct"]),
            "ca_p_resultado": float(linha["ca_p_ratio"]),
            "dieta_ms_pct": float(linha["dieta_ms_pct"]),
        }
        return referencia, componentes
