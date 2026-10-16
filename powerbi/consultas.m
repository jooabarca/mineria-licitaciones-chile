// Consultas de Power Query (M) - Licitaciones mineras en Mercado Publico
// Como usarlas: Power BI Desktop > Obtener datos > Consulta en blanco > Editor avanzado,
// pega el bloque de UNA tabla (desde "let" hasta el ultimo "in ...") y ponle de nombre el de la cabecera.
// Repite para las 10 tablas. Origen: Web anonimo, nivel de privacidad "Publico".
// La URL base va como texto fijo y el archivo en RelativePath: es la forma que el servicio de Power BI
// puede actualizar sin gateway (Web.Contents con URL armada dinamicamente NO se actualiza).
// Los tipos se convierten con la cultura "en-US" para que decimales y fechas no dependan de tu Windows (es-CL).
// Nota: no se pudo probar en Power BI Desktop desde esta sesion; la primera vez revisa que no haya errores de tipo.

// ===================== dim_fecha =====================
let
    Fuente = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "dim_fecha.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Fuente, [PromoteAllScalars = true]),
    // por si el archivo trae BOM, se asegura el nombre de la primera columna
    PrimeraColumna = Table.RenameColumns(Encabezados, {{Table.ColumnNames(Encabezados){0}, "fecha"}}),
    Tipos = Table.TransformColumnTypes(PrimeraColumna, {
        {"fecha", type date},
        {"anio", Int64.Type},
        {"mes_num", Int64.Type},
        {"mes", type text},
        {"anio_mes", type text},
        {"trimestre", type text},
        {"inicio_mes", type date},
        {"dia_semana_num", Int64.Type}
    }, "en-US")
in
    Tipos

// ===================== dim_region =====================
let
    Fuente = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "dim_region.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Fuente, [PromoteAllScalars = true]),
    // por si el archivo trae BOM, se asegura el nombre de la primera columna
    PrimeraColumna = Table.RenameColumns(Encabezados, {{Table.ColumnNames(Encabezados){0}, "region_id"}}),
    Tipos = Table.TransformColumnTypes(PrimeraColumna, {
        {"region_id", Int64.Type},
        {"region", type text},
        {"orden_norte_sur", Int64.Type}
    }, "en-US")
in
    Tipos

// ===================== dim_organismo =====================
let
    Fuente = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "dim_organismo.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Fuente, [PromoteAllScalars = true]),
    // por si el archivo trae BOM, se asegura el nombre de la primera columna
    PrimeraColumna = Table.RenameColumns(Encabezados, {{Table.ColumnNames(Encabezados){0}, "organismo_id"}}),
    Tipos = Table.TransformColumnTypes(PrimeraColumna, {
        {"organismo_id", Int64.Type},
        {"organismo", type text},
        {"sector", type text}
    }, "en-US")
in
    Tipos

// ===================== dim_proveedor =====================
let
    Fuente = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "dim_proveedor.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Fuente, [PromoteAllScalars = true]),
    // por si el archivo trae BOM, se asegura el nombre de la primera columna
    PrimeraColumna = Table.RenameColumns(Encabezados, {{Table.ColumnNames(Encabezados){0}, "proveedor_id"}}),
    Tipos = Table.TransformColumnTypes(PrimeraColumna, {
        {"proveedor_id", Int64.Type},
        {"nombre", type text},
        {"razon_social", type text},
        {"tipo_proveedor", type text}
    }, "en-US")
in
    Tipos

// ===================== dim_unspsc =====================
let
    Fuente = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "dim_unspsc.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Fuente, [PromoteAllScalars = true]),
    // por si el archivo trae BOM, se asegura el nombre de la primera columna
    PrimeraColumna = Table.RenameColumns(Encabezados, {{Table.ColumnNames(Encabezados){0}, "unspsc"}}),
    Tipos = Table.TransformColumnTypes(PrimeraColumna, {
        {"unspsc", type text},
        {"rubro1", type text},
        {"rubro2", type text},
        {"rubro3", type text},
        {"producto", type text},
        {"segmento", type text}
    }, "en-US")
in
    Tipos

// ===================== dim_estado =====================
let
    Fuente = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "dim_estado.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Fuente, [PromoteAllScalars = true]),
    // por si el archivo trae BOM, se asegura el nombre de la primera columna
    PrimeraColumna = Table.RenameColumns(Encabezados, {{Table.ColumnNames(Encabezados){0}, "estado_id"}}),
    Tipos = Table.TransformColumnTypes(PrimeraColumna, {
        {"estado_id", Int64.Type},
        {"estado_grupo", type text}
    }, "en-US")
in
    Tipos

// ===================== fact_licitacion =====================
let
    Fuente = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "fact_licitacion.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Fuente, [PromoteAllScalars = true]),
    // por si el archivo trae BOM, se asegura el nombre de la primera columna
    PrimeraColumna = Table.RenameColumns(Encabezados, {{Table.ColumnNames(Encabezados){0}, "licitacion_id"}}),
    Tipos = Table.TransformColumnTypes(PrimeraColumna, {
        {"licitacion_id", Int64.Type},
        {"codigo_externo", type text},
        {"nombre", type text},
        {"descripcion", type text},
        {"tipo", type text},
        {"tipo_compra", type text},
        {"estado", type text},
        {"organismo_id", Int64.Type},
        {"region_id", Int64.Type},
        {"comuna", type text},
        {"fecha_publicacion", type date},
        {"fecha_cierre", type date},
        {"moneda", type text},
        {"numero_oferentes", Int64.Type},
        {"mes_archivo", type text},
        {"n_proveedores_adjudicados", Int64.Type},
        {"fecha_adjudicacion", type date},
        {"n_items", Int64.Type},
        {"motivo_filtro", type text},
        {"categoria_relevancia", type text},
        {"monto_estimado_clp", type number},
        {"monto_adjudicado_clp", type number},
        {"dias_publicacion_a_cierre", Int64.Type},
        {"estado_id", Int64.Type}
    }, "en-US")
in
    Tipos

// ===================== fact_item =====================
let
    Fuente = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "fact_item.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Fuente, [PromoteAllScalars = true]),
    // por si el archivo trae BOM, se asegura el nombre de la primera columna
    PrimeraColumna = Table.RenameColumns(Encabezados, {{Table.ColumnNames(Encabezados){0}, "licitacion_id"}}),
    Tipos = Table.TransformColumnTypes(PrimeraColumna, {
        {"licitacion_id", Int64.Type},
        {"item_id", Int64.Type},
        {"unspsc", type text},
        {"producto", type text},
        {"cantidad", type number},
        {"n_ofertas", Int64.Type},
        {"proveedor_adjudicado_id", Int64.Type},
        {"monto_adjudicado_clp", type number}
    }, "en-US")
in
    Tipos

// ===================== fact_oferta =====================
let
    Fuente = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "fact_oferta.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Fuente, [PromoteAllScalars = true]),
    // por si el archivo trae BOM, se asegura el nombre de la primera columna
    PrimeraColumna = Table.RenameColumns(Encabezados, {{Table.ColumnNames(Encabezados){0}, "licitacion_id"}}),
    Tipos = Table.TransformColumnTypes(PrimeraColumna, {
        {"licitacion_id", Int64.Type},
        {"item_id", Int64.Type},
        {"proveedor_id", Int64.Type},
        {"estado_oferta", type text},
        {"seleccionada", Int64.Type},
        {"cantidad_ofertada", type number},
        {"monto_unitario", type number},
        {"valor_total_ofertado", type number},
        {"monto_adjudicado_linea", type number},
        {"moneda_oferta", type text},
        {"fecha_envio_oferta", type date}
    }, "en-US")
in
    Tipos

// ===================== meta =====================
let
    Fuente = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "meta.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Fuente, [PromoteAllScalars = true]),
    // por si el archivo trae BOM, se asegura el nombre de la primera columna
    PrimeraColumna = Table.RenameColumns(Encabezados, {{Table.ColumnNames(Encabezados){0}, "ejecutado_utc"}}),
    Tipos = Table.TransformColumnTypes(PrimeraColumna, {
        {"ejecutado_utc", type datetime},
        {"datos_hasta_publicacion", type date},
        {"meses_en_historia", Int64.Type},
        {"licitaciones", Int64.Type},
        {"ofertas", Int64.Type},
        {"fuente", type text}
    }, "en-US")
in
    Tipos
