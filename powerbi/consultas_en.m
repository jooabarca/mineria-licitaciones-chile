// Power Query (M) queries - Mining tenders in Mercado Publico (Chile)
// How to use: Power BI Desktop > Home > Transform data > Home > New Source > Blank Query > Home > Advanced Editor.
// Paste ONE block (from "let" to the last "in ChangedTypes"), click Done, and rename the query to the header name.
// Repeat for the 10 tables. If asked for credentials: Anonymous, privacy level Public.
// Base URL is fixed text and the file goes in RelativePath, so the Power BI service can refresh it without a gateway.
// Types are converted with the "en-US" culture so decimals/dates do not depend on your Windows regional settings.

// ===================== dim_fecha =====================
let
    Source = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "dim_fecha.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // makes sure the first column name is clean even if the file has a BOM
    RenamedFirstColumn = Table.RenameColumns(PromotedHeaders, {{Table.ColumnNames(PromotedHeaders){0}, "fecha"}}),
    ChangedTypes = Table.TransformColumnTypes(RenamedFirstColumn, {
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
    ChangedTypes

// ===================== dim_region =====================
let
    Source = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "dim_region.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // makes sure the first column name is clean even if the file has a BOM
    RenamedFirstColumn = Table.RenameColumns(PromotedHeaders, {{Table.ColumnNames(PromotedHeaders){0}, "region_id"}}),
    ChangedTypes = Table.TransformColumnTypes(RenamedFirstColumn, {
        {"region_id", Int64.Type},
        {"region", type text},
        {"orden_norte_sur", Int64.Type}
    }, "en-US")
in
    ChangedTypes

// ===================== dim_organismo =====================
let
    Source = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "dim_organismo.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // makes sure the first column name is clean even if the file has a BOM
    RenamedFirstColumn = Table.RenameColumns(PromotedHeaders, {{Table.ColumnNames(PromotedHeaders){0}, "organismo_id"}}),
    ChangedTypes = Table.TransformColumnTypes(RenamedFirstColumn, {
        {"organismo_id", Int64.Type},
        {"organismo", type text},
        {"sector", type text}
    }, "en-US")
in
    ChangedTypes

// ===================== dim_proveedor =====================
let
    Source = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "dim_proveedor.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // makes sure the first column name is clean even if the file has a BOM
    RenamedFirstColumn = Table.RenameColumns(PromotedHeaders, {{Table.ColumnNames(PromotedHeaders){0}, "proveedor_id"}}),
    ChangedTypes = Table.TransformColumnTypes(RenamedFirstColumn, {
        {"proveedor_id", Int64.Type},
        {"nombre", type text},
        {"razon_social", type text},
        {"tipo_proveedor", type text}
    }, "en-US")
in
    ChangedTypes

// ===================== dim_unspsc =====================
let
    Source = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "dim_unspsc.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // makes sure the first column name is clean even if the file has a BOM
    RenamedFirstColumn = Table.RenameColumns(PromotedHeaders, {{Table.ColumnNames(PromotedHeaders){0}, "unspsc"}}),
    ChangedTypes = Table.TransformColumnTypes(RenamedFirstColumn, {
        {"unspsc", type text},
        {"rubro1", type text},
        {"rubro2", type text},
        {"rubro3", type text},
        {"producto", type text},
        {"segmento", type text}
    }, "en-US")
in
    ChangedTypes

// ===================== dim_estado =====================
let
    Source = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "dim_estado.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // makes sure the first column name is clean even if the file has a BOM
    RenamedFirstColumn = Table.RenameColumns(PromotedHeaders, {{Table.ColumnNames(PromotedHeaders){0}, "estado_id"}}),
    ChangedTypes = Table.TransformColumnTypes(RenamedFirstColumn, {
        {"estado_id", Int64.Type},
        {"estado_grupo", type text}
    }, "en-US")
in
    ChangedTypes

// ===================== fact_licitacion =====================
let
    Source = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "fact_licitacion.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // makes sure the first column name is clean even if the file has a BOM
    RenamedFirstColumn = Table.RenameColumns(PromotedHeaders, {{Table.ColumnNames(PromotedHeaders){0}, "licitacion_id"}}),
    ChangedTypes = Table.TransformColumnTypes(RenamedFirstColumn, {
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
    ChangedTypes

// ===================== fact_item =====================
let
    Source = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "fact_item.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // makes sure the first column name is clean even if the file has a BOM
    RenamedFirstColumn = Table.RenameColumns(PromotedHeaders, {{Table.ColumnNames(PromotedHeaders){0}, "licitacion_id"}}),
    ChangedTypes = Table.TransformColumnTypes(RenamedFirstColumn, {
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
    ChangedTypes

// ===================== fact_oferta =====================
let
    Source = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "fact_oferta.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // makes sure the first column name is clean even if the file has a BOM
    RenamedFirstColumn = Table.RenameColumns(PromotedHeaders, {{Table.ColumnNames(PromotedHeaders){0}, "licitacion_id"}}),
    ChangedTypes = Table.TransformColumnTypes(RenamedFirstColumn, {
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
    ChangedTypes

// ===================== meta =====================
let
    Source = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/jooabarca/mineria-licitaciones-chile/main/data/", [RelativePath = "meta.csv"]),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // makes sure the first column name is clean even if the file has a BOM
    RenamedFirstColumn = Table.RenameColumns(PromotedHeaders, {{Table.ColumnNames(PromotedHeaders){0}, "ejecutado_utc"}}),
    ChangedTypes = Table.TransformColumnTypes(RenamedFirstColumn, {
        {"ejecutado_utc", type datetime},
        {"datos_hasta_publicacion", type date},
        {"meses_en_historia", Int64.Type},
        {"licitaciones", Int64.Type},
        {"ofertas", Int64.Type},
        {"fuente", type text}
    }, "en-US")
in
    ChangedTypes
