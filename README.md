# Licitaciones del sector minero en Mercado Público (Chile)

Job diario y gratuito que descarga los archivos mensuales de **Datos Abiertos de ChileCompra**, filtra la
**minería estricta**, acumula 24 meses de historia y deja un modelo en estrella (CSV) listo para Power BI.
No usa el ticket de la API ni ningún secreto. Datos públicos de la Dirección ChileCompra.

> Estado: backfill de 24 meses ejecutado (2024-10 a 2026-10, 25 archivos) y modelo generado en `data/`.
> El workflow de GitHub Actions corrió una vez a mano (16-oct-2026, 40 s, verde) y quedó programado a diario (20:00 UTC).

## Qué se midió (histórico real, 2024-10 a 2026-10)

- **690 licitaciones mineras** (~7.000-9.000 licitaciones con ofertas por mes en total): entre 16 y 36 al mes
  (octubre de 2024 llegó a 64, y octubre de 2026 va a medio mes). 520 adjudicadas, 95 desiertas, 17 revocadas,
  58 cerradas sin adjudicar.
- **Monto adjudicado: ~21.800 millones de CLP** (estimado ~50.100 millones). Lo mueve la maquinaria
  (~11.900 millones en 286 licitaciones); las compras administrativas del sector suman ~6.400 millones en 313.
- Compradores principales: Sernageomin (239), Subsecretaría de Minería (61), MOP/Vialidad (31), universidades,
  División Logística del Ejército y Cochilco (14). **Codelco y ENAMI no aparecen.**
- Proveedores que más ganan por monto: Komatsu Chile, DIEXA, Finning Chile, PESCO, Dercomaq. 545 proveedores
  distintos ganaron al menos una línea.
- 263 filas del archivo de marzo de 2026 venían corruptas en origen (saltos de línea dentro de un campo) y se
  descartan; el pipeline lo avisa en el log.
- Es un dashboard sobre **cómo compra el Estado en torno a la minería**, no sobre el mercado minero privado.
  El 45 % de las licitaciones son compras administrativas de organismos del sector (aseo, EPP, software).

## Qué trae cada archivo mensual (y qué no)

- Solo licitaciones **ya cerradas y con ofertas** (oct: publicadas hasta el día 9, cierre hasta el 15; ninguna abierta,
  ninguna sin ofertas). Por eso **las "abiertas hoy" no salen de aquí** (ver "Abiertas" abajo).
- Latin-1, separador `;`, 110 columnas, una fila por licitación × ítem × oferente. Los montos de la licitación se repiten
  en cada fila: el pipeline deduplica. La oferta ganadora es `Oferta seleccionada` + `MontoLineaAdjudica`.
- Los archivos de meses anteriores se regeneran a diario (cambian las adjudicaciones), por eso cada corrida
  re-descarga el mes actual y los 2 previos.

## Filtro "minería estricta" (`pipeline/build.py`)

Una licitación entra si alguna fila cumple una de estas reglas:

1. **Organismo del sector**: Sernageomin, Ministerio/Subsecretaría/Seremi de Minería, Cochilco, ENAMI, Codelco.
2. **UNSPSC minero**: familias 2010 (maquinaria de minería) y 2011 (perforación y exploración), sin los códigos
   usados como comodín (transporte de personal, vehículos de servicio, inspección de alcantarillado).
3. **Palabra clave fuerte** en nombre/descripción/línea: minería, minero/a, relave, yacimiento, tronadura,
   sondaje minero, chancadora, faena minera, pirquinero. Exclusiones: "minería de datos", royalty, agua mineral.

Cada licitación queda clasificada: *Maquinaria de minería y perforación (UNSPSC)*, *Insumos y servicios mineros
(palabras clave)* o *Compra administrativa de organismo del sector* (para no mezclar aseo de Sernageomin con
maquinaria). Palabras descartadas por falsos positivos: faena (asfalto), chancado (áridos viales), tronadura
(rayos X), geotecnia (mecánica de suelos), cobre (cables).

## Modelo (carpeta `data/`)

| Tabla | Grano |
|---|---|
| `fact_licitacion` | 1 fila por licitación (montos en CLP solo si la moneda es CLP; `categoria_relevancia`, `motivo_filtro`) |
| `fact_item` | licitación × ítem (UNSPSC, cantidad, monto adjudicado, proveedor adjudicado) |
| `fact_oferta` | licitación × ítem × oferente (`seleccionada` 0/1) |
| `dim_organismo`, `dim_region`, `dim_unspsc`, `dim_proveedor`, `dim_estado`, `dim_fecha` | dimensiones |
| `meta.csv` | `ejecutado_utc`, `datos_hasta_publicacion`, filas: la usa el dashboard para mostrar la última actualización |

Relaciones (1 → *): `dim_organismo`, `dim_region`, `dim_estado` → `fact_licitacion`; `dim_fecha[fecha]` →
`fact_licitacion[fecha_publicacion]` (activa) y `[fecha_cierre]`, `[fecha_adjudicacion]` (inactivas);
`fact_licitacion[licitacion_id]` → `fact_item` y `fact_oferta`; `dim_unspsc[unspsc]` → `fact_item[unspsc]`;
`dim_proveedor` → `fact_oferta[proveedor_id]` (y `fact_item[proveedor_adjudicado_id]`, inactiva).

**Privacidad**: no se publica RUT; los proveedores que son personas naturales (RUT < 50.000.000) salen como
"Persona natural N".

## Cómo correrlo

```bash
pip install -r requirements.txt
python pipeline/build.py --backfill --desde 2024-10      # primera vez: historia (25 zips, ~360 MB en total)
python pipeline/build.py                                 # diario: mes actual + 2 previos
python pipeline/build.py --usar-cache --cache <carpeta> --desde 2026-09   # sin red, con zips ya bajados
```

`data/slices/AAAA-MM.csv.gz` guarda solo las filas mineras de cada mes (decenas de KB): es la historia acumulada.
`.github/workflows/actualizar.yml` ejecuta el job a diario (20:00 UTC) y hace commit de `data/` si cambió.
GitHub puede desactivar los workflows programados de repos sin actividad (60 días); el commit diario de datos
debería evitarlo, pero conviene revisarlo la primera vez.

## Conectar Power BI

Repo público con los CSV en `data/`. En Power BI Desktop: *Obtener datos → Web* con una URL fija por tabla, por ejemplo
`https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/fact_licitacion.csv`. Con URLs estáticas y anónimas, la
actualización programada del servicio no necesita gateway ni credenciales. No construyas la URL con parámetros dinámicos
(`Web.Contents` dinámico no se refresca en el servicio, salvo `RelativePath`/`Query`).

## Cómo comprobar que se actualiza solo

1. Una tarjeta con `meta[datos_hasta_publicacion]` y `meta[ejecutado_utc]` dentro del propio dashboard.
2. En GitHub, pestaña *Actions*: una ejecución diaria en verde; en *Commits*, `datos: actualización AAAA-MM-DD`.
3. En Power BI Service: *Actualizar → Historial de actualización* del modelo semántico.
4. Compara dos días seguidos: debería cambiar `ejecutado_utc` y, cuando ChileCompra publique, `datos_hasta_publicacion`.

El servicio pausa la actualización programada tras 2 meses sin visitas al informe y la desactiva tras 4 fallos
seguidos. Con "Publicar en la web" los datos se cachean 1 hora.

## Abiertas hoy (opcional, requiere el ticket)

Los zips no incluyen licitaciones abiertas. Para eso habría que sumar un segundo paso con la API
(`estado=activas`, filtrar por nombre y consultar el detalle solo de las candidatas, ~2,3 s por consulta). El ticket
iría solo como secreto de GitHub Actions (`MP_TICKET`), nunca en el repo ni en los CSV. **No está implementado.**
La clasificación por título tiene menos precisión que la del archivo masivo, porque el listado no trae UNSPSC.

## Vistas propuestas

Tarjetas (licitaciones, monto adjudicado, oferentes promedio, última actualización); tendencia mensual; por región
y por tipo de compra; organismos que más compran; proveedores que más ganan (monto y n.º de adjudicaciones);
mapa de categorías de relevancia; días de publicación a cierre; tabla de licitaciones con drill-through a ofertas.
