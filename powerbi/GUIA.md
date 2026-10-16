# Guía Power BI: licitaciones mineras (Mercado Público)

Archivos de esta carpeta: `consultas.m` (10 consultas de Power Query), `medidas.dax` (medidas) y esta guía.
Nada de esto se pudo probar en Power BI Desktop desde la sesión que lo preparó: en la primera carga revisa que no
haya errores de tipo (ver "Si algo falla").

## 1. Cargar los datos (Power Query)

1. Power BI Desktop → **Obtener datos → Consulta en blanco → Editor avanzado**.
2. Pega un bloque de `consultas.m` (de `let` a `in Tipos`) y ponle **el nombre de la cabecera** (`dim_fecha`, `fact_licitacion`…).
3. Repite para las 10 tablas: `dim_fecha`, `dim_region`, `dim_organismo`, `dim_proveedor`, `dim_unspsc`, `dim_estado`,
   `fact_licitacion`, `fact_item`, `fact_oferta`, `meta`.
4. Si pide credenciales: **Anónimo**, y nivel de privacidad **Público**. Cerrar y aplicar.

La URL base va como texto fijo y el archivo en `RelativePath`: es lo que permite que el servicio actualice sin gateway.
Si algún día cambias de repo o rama, edita la URL en cada consulta (o pídeme que regenere `consultas.m`).

## 2. Modelo

Marca `dim_fecha` como **tabla de fechas** (columna `fecha`). Ordena `mes` por `mes_num`. Oculta las claves
(`*_id`, `licitacion_id`, `item_id`) en las tablas de hechos.

| Desde (1) | Hacia (*) | Estado |
|---|---|---|
| `dim_fecha[fecha]` | `fact_licitacion[fecha_publicacion]` | **Activa** |
| `dim_fecha[fecha]` | `fact_licitacion[fecha_cierre]` | Inactiva |
| `dim_fecha[fecha]` | `fact_licitacion[fecha_adjudicacion]` | Inactiva |
| `dim_organismo[organismo_id]` | `fact_licitacion[organismo_id]` | Activa |
| `dim_region[region_id]` | `fact_licitacion[region_id]` | Activa |
| `dim_estado[estado_id]` | `fact_licitacion[estado_id]` | Activa |
| `fact_licitacion[licitacion_id]` | `fact_item[licitacion_id]` | Activa (un solo sentido) |
| `fact_licitacion[licitacion_id]` | `fact_oferta[licitacion_id]` | Activa (un solo sentido) |
| `dim_unspsc[unspsc]` | `fact_item[unspsc]` | Activa |
| `dim_proveedor[proveedor_id]` | `fact_oferta[proveedor_id]` | Activa |
| `dim_proveedor[proveedor_id]` | `fact_item[proveedor_adjudicado_id]` | Inactiva |

`meta` no se relaciona con nada (solo alimenta la tarjeta de "última actualización").
Power BI intentará crear relaciones solo; revísalas contra esta tabla, porque podría activar `fecha_cierre` o
`fecha_adjudicacion` en vez de `fecha_publicacion`.

## 3. Medidas

Crea `_Medidas` (Inicio → Especificar datos) y agrega cada medida de `medidas.dax`. Formatos: montos `#,0`,
porcentajes `0.0%`. Las medidas están en el modelo, no a nivel de informe (requisito de "Publicar en la web").

## 4. Páginas

Tamaño 16:9, tema oscuro sobrio, un color de acento por categoría de relevancia (maquinaria, insumos, administrativas).
En **todas** las páginas: tarjeta con `[Texto de actualización]` abajo y nota "Fuente: ChileCompra, Datos Abiertos.
Solo licitaciones cerradas con ofertas; no incluye abiertas."

**Página 1 · Resumen**
- Fila de tarjetas: Licitaciones, Monto adjudicado (CLP), % adjudicación, Oferentes promedio, Proveedores ganadores.
- Columnas por mes de publicación (`dim_fecha[anio_mes]`) con `[Licitaciones]`, apiladas por `categoria_relevancia`.
- Barras de `[Monto adjudicado (CLP)]` por `categoria_relevancia`.
- Segmentadores: año, región, categoría de relevancia, estado.

**Página 2 · Quién compra y dónde**
- Barras horizontales: top 10 organismos por `[Licitaciones]` (tooltip con monto adjudicado).
- Barras por región ordenadas norte → sur (`orden_norte_sur`).
- Dona o barra por tipo de compra (`tipo`: L1, LE, LP, LQ, LR) y por `sector` del organismo.
- Matriz organismo × categoría de relevancia.

**Página 3 · Quién gana**
- Tabla/barras: top 15 proveedores por `[Monto ganado (CLP)]`, con `[Licitaciones ganadas]`, `[Tasa de éxito]`.
- Tarjeta `[Concentración top 5 %]` y `[% con un solo oferente]`.
- Dispersión: eje X = licitaciones en que participó, eje Y = tasa de éxito, tamaño = monto ganado.
- Segmentador por `tipo_proveedor` y por categoría.

**Página 4 · Detalle**
- Tabla de licitaciones: `codigo_externo`, `nombre`, organismo, región, estado, fechas, `monto_estimado_clp`, oferentes.
- Drill-through desde las otras páginas: ítems (`fact_item` con `dim_unspsc[producto]`) y ofertas del proceso.
- Botón/enlace a la ficha oficial: `https://www.mercadopublico.cl/fichaLicitacion.html?idLicitacion=` + `codigo_externo`.

## 5. Publicar y que se actualice solo

1. Licencia y administrador: ver `README.md` (correo laboral/educacional, Pro o "Mi área de trabajo", ajuste de
   administrador "Publicar en la web").
2. Publicar el informe → modelo semántico → **Credenciales de origen**: Web, Anónimo, nivel de privacidad Público.
3. **Actualización programada**: 1 vez al día, por ejemplo 17:30 hora de Chile (el workflow de GitHub corre 20:00 UTC;
   en Pro hay hasta 8 al día).
4. **Archivo → Insertar informe → Publicar en la web** (solo importación, sin RLS ni DirectQuery) y pegar el iframe en
   joseabarca.com.
5. Comprobar: la tarjeta `[Texto de actualización]` cambia al día siguiente, el historial de actualización del modelo
   muestra ejecuciones diarias en verde y GitHub muestra el commit `datos: actualización AAAA-MM-DD`.

## Si algo falla

- **Error al convertir tipos**: normalmente un valor inesperado en una columna numérica. Quita ese tipo en la consulta
  y avísame qué columna era.
- **"Origen de datos dinámico"**: revisa que la URL base siga siendo texto fijo con `RelativePath`.
- **Fechas como texto o números con coma**: las consultas usan cultura `"en-US"`; no la quites.
- **Relaciones ambiguas**: deja inactivas las de `fecha_cierre`, `fecha_adjudicacion` y `fact_item[proveedor_adjudicado_id]`.
