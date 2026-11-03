from pathlib import Path

import typer

from etl.bronze.api_client import InfoclimatClient
from etl.config import Settings
from etl.gold import runner as gold_runner
from etl.silver import runner as silver_runner

app = typer.Typer(help="ETL Infoclimat - archi médaillon (Bronze/Silver/Gold)")


def _load(config: Path) -> Settings:
    return Settings.load(config)


@app.command()
def bronze(
    config: Path = typer.Option("config.yaml"),
    job: str | None = typer.Option(None, help="Un seul job (sinon tous)"),
) -> None:
    """Ingestion brute depuis l'API vers data/bronze/."""
    settings = _load(config)
    with InfoclimatClient(
        settings.api.base_url, settings.api.timeout_seconds
    ) as client:
        for ref in settings.bronze.references:
            if job and ref.name != job:
                continue
            out = settings.paths.bronze_dir / ref.output
            typer.echo(f"[bronze/ref] {ref.name} {ref.endpoint} -> {out}")
            client.fetch_to_file(ref.endpoint, out, ref.params)

        for ser in settings.bronze.series:
            if job and ser.name != job:
                continue
            out_dir = settings.paths.bronze_dir / ser.output_dir
            typer.echo(f"[bronze/series] {ser.name} {ser.endpoint} -> {out_dir}/")
            pages = client.fetch_paginated_to_dir(ser.endpoint, out_dir, ser.params)
            typer.echo(f"[bronze/series] {ser.name}: {len(pages)} page(s)")


@app.command()
def silver(job: str | None = typer.Option(None, help="Un seul SQL (sinon tous)")) -> None:
    """Nettoyage + typage Bronze -> Silver (SQL DuckDB)."""
    executed = silver_runner.run_all(job)
    for sql in executed:
        typer.echo(f"[silver] {sql.name}")
    if not executed:
        typer.echo("[silver] aucun fichier SQL exécuté")


@app.command()
def gold(job: str | None = typer.Option(None, help="Un seul SQL (sinon tous)")) -> None:
    """Agrégats et produits métier Silver -> Gold (SQL DuckDB)."""
    executed = gold_runner.run_all(job)
    for sql in executed:
        typer.echo(f"[gold] {sql.name}")
    if not executed:
        typer.echo("[gold] aucun fichier SQL exécuté")


@app.command("all")
def run_all(config: Path = typer.Option("config.yaml")) -> None:
    """Exécute bronze -> silver -> gold en séquence."""
    bronze(config=config, job=None)
    silver(job=None)
    gold(job=None)


@app.command("list")
def list_jobs(config: Path = typer.Option("config.yaml")) -> None:
    settings = _load(config)
    typer.echo("Bronze (references):")
    for r in settings.bronze.references:
        typer.echo(f"  - {r.name}  ({r.endpoint})")
    typer.echo("Bronze (series):")
    for s in settings.bronze.series:
        typer.echo(f"  - {s.name}  ({s.endpoint}) params={s.params}")
    typer.echo("Silver SQL:")
    for p in silver_runner.list_sql_files():
        typer.echo(f"  - {p.stem}")
    typer.echo("Gold SQL:")
    for p in gold_runner.list_sql_files():
        typer.echo(f"  - {p.stem}")


if __name__ == "__main__":
    app()
