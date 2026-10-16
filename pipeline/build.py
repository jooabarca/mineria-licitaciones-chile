#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Licitaciones del sector minero en Mercado Público (ChileCompra) -> tablas para Power BI.

Qué hace
  1. Descarga los zips mensuales de Datos Abiertos (sin ticket, sin clave):
         https://transparenciachc.blob.core.windows.net/lic-da/AAAA-M.zip
  2. Filtra "minería estricta" (ver FILTRO más abajo) y guarda solo esas licitaciones
     como "rebanadas" mensuales en data/slices/ (pocas filas; son la historia acumulada).
  3. Consolida todas las rebanadas en un modelo en estrella (CSV) en data/.

Modos
  python pipeline/build.py                       # diario: re-descarga el mes actual y 2 previos
  python pipeline/build.py --backfill --desde 2024-10   # histórico completo
  python pipeline/build.py --usar-cache --cache <carpeta con AAAA-M.zip>   # sin red

Solo usa biblioteca estándar + pandas. No usa ningún secreto.
Datos fuente: públicos (Dirección ChileCompra). Se omiten RUT y se enmascaran
proveedores que son personas naturales.
"""
import argparse
import codecs
import re
import shutil
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

URL = "https://transparenciachc.blob.core.windows.net/lic-da/{y}-{m}.zip"
RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
SLICES = DATA / "slices"
MESES_DIARIO = 3                       # mes actual + 2 previos (las adjudicaciones siguen cambiando)
MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
            "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# ------------------------------------------------------------------ FILTRO "minería estricta"
# Un proceso entra si CUALQUIER fila (ítem u oferta) cumple alguna de estas tres reglas.
# Medido en sep-2026: ~42 de 6.917 licitaciones (0,6 %). Calibrado a mano contra falsos positivos:
# "faena" (asfalto), "chancado" (áridos viales), "tronadura" (rayos X), "geotecnia" (mecánica de suelos)
# y "cobre" (cables) NO son señal minera y quedaron fuera.
ORGANISMOS = re.compile(
    r"GEOLOGIA Y MINERIA|SERNAGEOMIN|MINISTERIO DE MINERIA|SUBSECRETARIA.*MINERIA|SEREMI.*MINERIA|"
    r"COCHILCO|COMISION CHILENA DEL COBRE|ENAMI|EMPRESA NACIONAL DE MINERIA|CODELCO|CORPORACION NACIONAL DEL COBRE")
# Segmento 20 = maquinaria de minería y perforación, pero solo sirven las familias 2010 (maquinaria
# de minería) y 2011 (perforación y exploración). 2012-2014 son petróleo y gas, y el segmento trae
# códigos usados como comodín por organismos (traslado de personal, vehículos, cables, etc.).
UNSPSC_FAMILIAS = ("2010", "2011")
UNSPSC_EXCLUIR = {"20102301", "20102305", "20111610"}   # transporte de personal, vehículos, inspección de alcantarillado
PALABRAS = re.compile(
    r"\bMINERIA\b|\bMINER[OA]S?\b|\bRELAVES?\b|\bYACIMIENTOS?\b|\bTRONADURA\b|\bSONDAJES? MINERO|"
    r"\bCHANCADORAS?\b|\bFAENAS? MINERA|\bPEQUENA MINERIA\b|\bPIRQUINER")
EXCLUSIONES = re.compile(r"MINERIA DE DATOS|\bROYALTY\b|AGUAS? MINERAL")

COLS = ["Codigo", "CodigoExterno", "Nombre", "Descripcion", "Tipo", "Tipo de Adquisicion", "Estado",
        "CodigoOrganismo", "NombreOrganismo", "sector", "ComunaUnidad", "RegionUnidad", "CodigoMoneda",
        "FechaPublicacion", "FechaCierre", "FechaAdjudicacion", "MontoEstimado", "NumeroOferentes",
        "Codigoitem", "CodigoProductoONU", "Rubro1", "Rubro2", "Rubro3", "Nombre producto genrico",
        "Nombre linea Adquisicion", "Cantidad", "CodigoProveedor", "RutProveedor", "NombreProveedor",
        "RazonSocialProveedor", "Estado Oferta", "Cantidad Ofertada", "Moneda de la Oferta",
        "MontoUnitarioOferta", "Valor Total Ofertado", "CantidadAdjudicada", "MontoLineaAdjudica",
        "FechaEnvioOferta", "Oferta seleccionada"]

REGIONES = [  # id, nombre corto, fragmento normalizado que lo identifica
    (1, "Arica y Parinacota", "ARICA"), (2, "Tarapacá", "TARAPACA"), (3, "Antofagasta", "ANTOFAGASTA"),
    (4, "Atacama", "ATACAMA"), (5, "Coquimbo", "COQUIMBO"), (6, "Valparaíso", "VALPARAISO"),
    (7, "Metropolitana", "METROPOLITANA"), (8, "O'Higgins", "HIGGINS"), (9, "Maule", "MAULE"),
    (10, "Ñuble", "NUBLE"), (11, "Biobío", "BIOBIO"), (12, "La Araucanía", "ARAUCANIA"),
    (13, "Los Ríos", "LOS RIOS"), (14, "Los Lagos", "LOS LAGOS"), (15, "Aysén", "AYSEN"),
    (16, "Magallanes", "MAGALLANES"),
]


# ------------------------------------------------------------------ utilidades
def sin_tildes(s):
    """Mayúsculas y sin tildes, para comparar texto."""
    return (s.fillna("").str.upper().str.normalize("NFKD")
            .str.encode("ascii", "ignore").str.decode("ascii"))


def num(s):
    """Número desde texto. Algunos valores vienen como '3,5e+07' (coma decimal + notación científica)."""
    return pd.to_numeric(s.astype("string").str.replace(",", ".", regex=False), errors="coerce")


def fecha(s):
    f = pd.to_datetime(s, errors="coerce")
    return f.where(f.dt.year > 1950)           # 1900-01-01 es el "nulo" de la fuente


def detectar_codificacion(fh):
    muestra = fh.read(2_000_000)
    fh.seek(0)
    try:
        codecs.getincrementaldecoder("utf-8")().decode(muestra, final=False)
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "latin-1"                      # los meses probados vienen en Latin-1/cp1252


def descargar(y, m, cache, usar_cache):
    destino = cache / f"{y}-{m}.zip"
    if usar_cache and destino.exists():
        return destino
    url = URL.format(y=y, m=m)
    for intento in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mineria-licitaciones/1.0 (portafolio personal)"})
            with urllib.request.urlopen(req, timeout=180) as r, open(destino, "wb") as out:
                shutil.copyfileobj(r, out)
            return destino
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except Exception as e:                # red caída, timeout, etc.
            err = e
        time.sleep(5 * intento)
    raise RuntimeError(f"No se pudo descargar {url}: {err}")


def leer_zip(path):
    with zipfile.ZipFile(path) as z:
        nombre = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nombre) as fh:
            buf = tempfile.SpooledTemporaryFile(max_size=64 * 1024 * 1024)
            shutil.copyfileobj(fh, buf)
        buf.seek(0)
        enc = detectar_codificacion(buf)
        partes = []
        for ch in pd.read_csv(buf, sep=";", encoding=enc, dtype=str, chunksize=100_000,
                              usecols=lambda c: c in COLS):
            partes.append(ch)
        df = pd.concat(partes, ignore_index=True)
    faltan = [c for c in COLS if c not in df.columns]
    if faltan:
        print(f"  aviso: faltan columnas {faltan}; se rellenan vacías")
        for c in faltan:
            df[c] = pd.NA
    df = df[COLS]
    # filas corruptas en origen (saltos de línea dentro de un campo desplazan las columnas)
    ok = df["Codigo"].fillna("").str.fullmatch(r"\d+") & df["Codigoitem"].fillna("").str.fullmatch(r"\d+")
    if not ok.all():
        print(f"  aviso: {int((~ok).sum())} fila(s) corruptas en el origen descartadas")
    return df[ok].reset_index(drop=True)


# ------------------------------------------------------------------ filtro
def aplicar_filtro(df):
    """Devuelve (filas de las licitaciones mineras, con columnas de motivo)."""
    org = sin_tildes(df["NombreOrganismo"]).str.contains(ORGANISMOS)
    cod = df["CodigoProductoONU"].fillna("")
    unspsc = cod.str.startswith(UNSPSC_FAMILIAS) & ~cod.isin(UNSPSC_EXCLUIR)
    texto = sin_tildes(df["Nombre"]) + " " + sin_tildes(df["Descripcion"]) + " " + sin_tildes(df["Nombre linea Adquisicion"])
    kw = texto.str.contains(PALABRAS) & ~texto.str.contains(EXCLUSIONES)
    flags = pd.DataFrame({"Codigo": df["Codigo"], "f_org": org, "f_unspsc": unspsc, "f_kw": kw})
    g = flags.groupby("Codigo")[["f_org", "f_unspsc", "f_kw"]].any()
    g = g[g.any(axis=1)]
    out = df[df["Codigo"].isin(g.index)].copy()
    out = out.join(g, on="Codigo")
    return out


def procesar_mes(y, m, cache, usar_cache):
    zip_path = descargar(y, m, cache, usar_cache)
    if zip_path is None:
        print(f"  {y}-{m}: no existe aún (404); se omite")
        return False
    df = leer_zip(zip_path)
    # RUT no se publica: solo marcamos personas naturales (RUT < 50.000.000)
    rut = pd.to_numeric(df["RutProveedor"].fillna("").str.replace(".", "", regex=False).str.split("-").str[0],
                        errors="coerce")
    df["persona_natural"] = (rut < 50_000_000).astype("Int8")
    pn = df["persona_natural"].eq(1)
    etiqueta = "Persona natural " + df["CodigoProveedor"].fillna("s/c")
    df.loc[pn, "NombreProveedor"] = etiqueta[pn]            # los nombres de personas no se guardan ni publican
    df.loc[pn, "RazonSocialProveedor"] = etiqueta[pn]
    out = aplicar_filtro(df).drop(columns=["RutProveedor"])
    out["mes_archivo"] = f"{y}-{int(m):02d}"
    SLICES.mkdir(parents=True, exist_ok=True)
    out.to_csv(SLICES / f"{y}-{int(m):02d}.csv.gz", index=False, encoding="utf-8", compression="gzip",
               lineterminator="\n")
    print(f"  {y}-{m}: {df['Codigo'].nunique():,} licitaciones en el archivo -> "
          f"{out['Codigo'].nunique():,} mineras ({len(out):,} filas)")
    return True


# ------------------------------------------------------------------ consolidación / modelo
def cargar_rebanadas():
    archivos = sorted(SLICES.glob("*.csv.gz"))
    if not archivos:
        raise SystemExit("No hay rebanadas en data/slices; corre primero la descarga.")
    df = pd.concat([pd.read_csv(a, dtype=str) for a in archivos], ignore_index=True)
    # si una licitación aparece en varios meses, se queda la versión del archivo más reciente
    ultimo = df.groupby("Codigo")["mes_archivo"].transform("max")
    return df[df["mes_archivo"] == ultimo].copy()


def region_id(s):
    n = sin_tildes(s)
    ids = pd.Series(pd.NA, index=s.index, dtype="Int64")
    for rid, _, frag in REGIONES:
        ids = ids.mask(n.str.contains(frag, regex=False) & ids.isna(), rid)
    return ids


def construir_modelo(df):
    df = df.copy()
    for c in ["MontoEstimado", "NumeroOferentes", "Cantidad", "Cantidad Ofertada", "MontoUnitarioOferta",
              "Valor Total Ofertado", "CantidadAdjudicada", "MontoLineaAdjudica"]:
        df[c] = num(df[c])
    for c in ["FechaPublicacion", "FechaCierre", "FechaAdjudicacion", "FechaEnvioOferta"]:
        df[c] = fecha(df[c])
    for c in ["f_org", "f_unspsc", "f_kw"]:
        df[c] = df[c].astype(str).str.lower().eq("true")
    df["persona_natural"] = pd.to_numeric(df["persona_natural"], errors="coerce")
    df["seleccionada"] = (df["Oferta seleccionada"] == "Seleccionada").astype("Int8")
    df["region_id"] = region_id(df["RegionUnidad"])
    df["clp"] = df["CodigoMoneda"].eq("CLP")
    df["proveedor_id"] = pd.to_numeric(df["CodigoProveedor"], errors="coerce").astype("Int64")

    # --- dim_region
    dim_region = pd.DataFrame([(i, n) for i, n, _ in REGIONES], columns=["region_id", "region"])
    dim_region["orden_norte_sur"] = dim_region["region_id"]

    # --- dim_organismo
    org = (df.sort_values("FechaPublicacion").groupby("CodigoOrganismo")
           .agg(organismo=("NombreOrganismo", "last"), sector=("sector", "last")).reset_index()
           .rename(columns={"CodigoOrganismo": "organismo_id"}))
    org["organismo_id"] = pd.to_numeric(org["organismo_id"]).astype("Int64")
    org["organismo"] = org["organismo"].str.strip()

    # --- dim_proveedor (sin RUT; personas naturales enmascaradas)
    pr = (df.dropna(subset=["proveedor_id"]).sort_values("FechaPublicacion").groupby("proveedor_id")
          .agg(nombre=("NombreProveedor", "last"), razon_social=("RazonSocialProveedor", "last"),
               persona_natural=("persona_natural", "max")).reset_index())
    mask = pr["persona_natural"].eq(1)
    pr.loc[mask, "nombre"] = "Persona natural " + pr.loc[mask, "proveedor_id"].astype(str)
    pr.loc[mask, "razon_social"] = pr.loc[mask, "nombre"]
    pr["tipo_proveedor"] = mask.map({True: "Persona natural", False: "Empresa"})
    dim_proveedor = pr.drop(columns=["persona_natural"])

    # --- dim_unspsc
    dim_unspsc = (df.dropna(subset=["CodigoProductoONU"]).groupby("CodigoProductoONU")
                  .agg(rubro1=("Rubro1", "first"), rubro2=("Rubro2", "first"), rubro3=("Rubro3", "first"),
                       producto=("Nombre producto genrico", "first")).reset_index()
                  .rename(columns={"CodigoProductoONU": "unspsc"}))
    dim_unspsc["segmento"] = dim_unspsc["unspsc"].str[:2]

    # --- fact_licitacion (1 fila por licitación)
    sel = df[df["seleccionada"] == 1]
    adj = sel.groupby("Codigo")["MontoLineaAdjudica"].sum().rename("monto_adjudicado")
    prov_ganadores = (sel.groupby("Codigo")["proveedor_id"].nunique().rename("n_proveedores_adjudicados"))
    primero = df.groupby("Codigo").first()
    lic = pd.DataFrame({
        "licitacion_id": primero.index,
        "codigo_externo": primero["CodigoExterno"].values,
        "nombre": primero["Nombre"].str.strip().values,
        "descripcion": primero["Descripcion"].fillna("").str.replace(r"\s+", " ", regex=True).str.slice(0, 600).values,
        "tipo": primero["Tipo"].values,
        "tipo_compra": primero["Tipo de Adquisicion"].values,
        "estado": primero["Estado"].values,
        "organismo_id": pd.to_numeric(primero["CodigoOrganismo"]).astype("Int64").values,
        "region_id": primero["region_id"].values,
        "comuna": primero["ComunaUnidad"].str.strip().values,
        "fecha_publicacion": primero["FechaPublicacion"].values,
        "fecha_cierre": primero["FechaCierre"].values,
        "moneda": primero["CodigoMoneda"].values,
        "monto_estimado": primero["MontoEstimado"].values,
        "numero_oferentes": primero["NumeroOferentes"].astype("Int64").values,
        "mes_archivo": primero["mes_archivo"].values,
    })
    lic = lic.merge(adj, left_on="licitacion_id", right_index=True, how="left")
    lic = lic.merge(prov_ganadores, left_on="licitacion_id", right_index=True, how="left")
    fa = df[df["Estado"].eq("Adjudicada")].groupby("Codigo")["FechaAdjudicacion"].first()
    lic["fecha_adjudicacion"] = lic["licitacion_id"].map(fa)
    lic["n_items"] = lic["licitacion_id"].map(df.groupby("Codigo")["Codigoitem"].nunique())
    flags = df.groupby("Codigo")[["f_org", "f_unspsc", "f_kw"]].any()
    motivos = flags.apply(lambda r: " + ".join(n for n, v in [("organismo del sector", r.f_org), ("UNSPSC minero", r.f_unspsc),
                                                              ("palabra clave", r.f_kw)] if v), axis=1)
    lic["motivo_filtro"] = lic["licitacion_id"].map(motivos)
    def _categoria(r):
        if r.f_unspsc:
            return "Maquinaria de minería y perforación (UNSPSC)"
        if r.f_kw and not r.f_org:      # si el comprador es del sector, "minería" suele ser solo su nombre
            return "Insumos y servicios mineros (palabras clave)"
        return "Compra administrativa de organismo del sector"
    lic["categoria_relevancia"] = lic["licitacion_id"].map(flags.apply(_categoria, axis=1))
    clp = lic["moneda"].eq("CLP")
    lic["monto_estimado_clp"] = lic["monto_estimado"].where(clp)
    lic["monto_adjudicado_clp"] = lic["monto_adjudicado"].where(clp)
    lic["dias_publicacion_a_cierre"] = (lic["fecha_cierre"] - lic["fecha_publicacion"]).dt.days
    lic = lic.drop(columns=["monto_estimado", "monto_adjudicado"])
    def _estado_id(e):
        e = str(e)
        return 1 if e == "Adjudicada" else 2 if e == "Cerrada" else 3 if e.startswith("Desierta") else 4 if e == "Revocada" else 5
    lic["estado_id"] = lic["estado"].map(_estado_id)

    # --- fact_item (licitación x ítem)
    it = df.groupby(["Codigo", "Codigoitem"]).agg(
        unspsc=("CodigoProductoONU", "first"), producto=("Nombre linea Adquisicion", "first"),
        cantidad=("Cantidad", "first"), n_ofertas=("proveedor_id", "count")).reset_index()
    gan_item = (sel.groupby(["Codigo", "Codigoitem"]).agg(
        monto_adjudicado=("MontoLineaAdjudica", "sum"), proveedor_adjudicado_id=("proveedor_id", "first")).reset_index())
    fact_item = it.merge(gan_item, on=["Codigo", "Codigoitem"], how="left")
    mon = df.groupby("Codigo")["clp"].first()
    fact_item["monto_adjudicado_clp"] = fact_item["monto_adjudicado"].where(fact_item["Codigo"].map(mon).fillna(False))
    fact_item = fact_item.drop(columns=["monto_adjudicado"]).rename(columns={"Codigo": "licitacion_id", "Codigoitem": "item_id"})
    fact_item["licitacion_id"] = fact_item["licitacion_id"].astype("Int64")

    # --- fact_oferta (licitación x ítem x oferente)
    fo = pd.DataFrame({
        "licitacion_id": pd.to_numeric(df["Codigo"]).astype("Int64"), "item_id": pd.to_numeric(df["Codigoitem"]).astype("Int64"),
        "proveedor_id": df["proveedor_id"], "estado_oferta": df["Estado Oferta"], "seleccionada": df["seleccionada"],
        "cantidad_ofertada": df["Cantidad Ofertada"], "monto_unitario": df["MontoUnitarioOferta"],
        "valor_total_ofertado": df["Valor Total Ofertado"], "monto_adjudicado_linea": df["MontoLineaAdjudica"],
        "moneda_oferta": df["Moneda de la Oferta"], "fecha_envio_oferta": df["FechaEnvioOferta"]})
    fact_item["licitacion_id"] = pd.to_numeric(fact_item["licitacion_id"]).astype("Int64")
    lic["licitacion_id"] = pd.to_numeric(lic["licitacion_id"]).astype("Int64")

    # --- dim_estado
    dim_estado = pd.DataFrame([(1, "Adjudicada"), (2, "Cerrada"), (3, "Desierta"), (4, "Revocada"), (5, "Otro")],
                              columns=["estado_id", "estado_grupo"])

    # --- dim_fecha (cubre publicación -> cierre/adjudicación)
    f0 = min(lic["fecha_publicacion"].min(), fo["fecha_envio_oferta"].min())
    f1 = max(lic["fecha_cierre"].max(), lic["fecha_adjudicacion"].max(), pd.Timestamp.today().normalize())
    dias = pd.date_range(f0.replace(day=1), f1 + pd.offsets.MonthEnd(0), freq="D")
    dim_fecha = pd.DataFrame({"fecha": dias})
    s = dim_fecha["fecha"].dt
    dim_fecha["anio"], dim_fecha["mes_num"] = s.year, s.month
    dim_fecha["mes"] = [MESES_ES[m - 1] for m in s.month]
    dim_fecha["anio_mes"] = s.strftime("%Y-%m")
    dim_fecha["trimestre"] = "T" + s.quarter.astype(str)
    dim_fecha["inicio_mes"] = s.to_period("M").dt.start_time
    dim_fecha["dia_semana_num"] = s.dayofweek + 1

    return dict(dim_fecha=dim_fecha, dim_region=dim_region, dim_organismo=org, dim_proveedor=dim_proveedor,
                dim_unspsc=dim_unspsc, dim_estado=dim_estado, fact_licitacion=lic, fact_item=fact_item,
                fact_oferta=fo)


def escribir(tablas, n_meses):
    DATA.mkdir(parents=True, exist_ok=True)
    for nombre, t in tablas.items():
        t = t.copy()
        for c in t.columns:
            if pd.api.types.is_datetime64_any_dtype(t[c]):
                t[c] = t[c].dt.strftime("%Y-%m-%d")
        t.to_csv(DATA / f"{nombre}.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
        print(f"  {nombre}.csv: {len(t):,} filas")
    lic = tablas["fact_licitacion"]
    meta = pd.DataFrame([{
        "ejecutado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "datos_hasta_publicacion": lic["fecha_publicacion"].max().strftime("%Y-%m-%d"),
        "meses_en_historia": n_meses, "licitaciones": len(lic), "ofertas": len(tablas["fact_oferta"]),
        "fuente": "ChileCompra - Datos Abiertos (licitaciones mensuales)"}])
    meta.to_csv(DATA / "meta.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    print("  meta.csv")


def rango_meses(desde, hasta):
    y, m = map(int, desde.split("-"))
    yh, mh = map(int, hasta.split("-"))
    while (y, m) <= (yh, mh):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default=None, help="AAAA-MM de inicio de la historia (por defecto 24 meses atrás)")
    ap.add_argument("--hasta", default=None, help="AAAA-MM final (por defecto el mes actual)")
    ap.add_argument("--backfill", action="store_true", help="re-descarga todos los meses del rango")
    ap.add_argument("--usar-cache", action="store_true", help="usa zips ya presentes en --cache (sin red)")
    ap.add_argument("--cache", default=None, help="carpeta de zips (por defecto una temporal)")
    ap.add_argument("--solo-consolidar", action="store_true", help="no descarga: reconstruye data/ desde las rebanadas")
    a = ap.parse_args()

    hoy = datetime.now(timezone.utc)
    hasta = a.hasta or f"{hoy.year}-{hoy.month:02d}"
    if a.desde:
        desde = a.desde
    else:
        y, m = hoy.year, hoy.month - 23
        while m < 1:
            y, m = y - 1, m + 12
        desde = f"{y}-{m:02d}"
    meses = list(rango_meses(desde, hasta))

    if not a.solo_consolidar:
        a_procesar = meses if a.backfill else meses[-MESES_DIARIO:]
        # meses del rango sin rebanada también se procesan (primera corrida)
        faltantes = [(y, m) for y, m in meses if not (SLICES / f"{y}-{m:02d}.csv.gz").exists()]
        a_procesar = sorted(set(a_procesar) | set(faltantes))
        cache = Path(a.cache) if a.cache else Path(tempfile.mkdtemp(prefix="lic-da-"))
        cache.mkdir(parents=True, exist_ok=True)
        print(f"Procesando {len(a_procesar)} mes(es): {a_procesar[0]} .. {a_procesar[-1]}")
        for y, m in a_procesar:
            procesar_mes(y, m, cache, a.usar_cache)
            time.sleep(1)
        if not a.cache:
            shutil.rmtree(cache, ignore_errors=True)

    df = cargar_rebanadas()
    print("Consolidando modelo...")
    tablas = construir_modelo(df)
    escribir(tablas, df["mes_archivo"].nunique())


if __name__ == "__main__":
    main()
