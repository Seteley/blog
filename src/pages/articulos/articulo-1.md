---
layout: ../../layouts/ArticleLayout.astro
title: "Investigación: Alfresco vs. Amazon S3 (600 ops/seg)"
description: "Comparativa técnica de throughput e I/O entre Alfresco Content Services y Amazon S3 dimensionados a 600 operaciones por segundo."
date: "2026-06-26"
---

# Investigación: Solución basada en Alfresco vs. solución basada en Amazon S3 (a 600 ops/seg)

> **Alcance del estudio:** comparativa técnica de **operaciones por segundo (ops/seg) e I/O** entre una arquitectura de gestión documental basada en **Alfresco Content Services (ACS)** y una arquitectura de almacenamiento de objetos basada en **Amazon S3**, dimensionando ambas para sostener un objetivo de **600 operaciones por segundo**.
> **Fecha:** junio 2026 · **Tipo:** análisis técnico con datos numéricos y referencias.

---

## 1. Objetivo

Analizar y comparar **Alfresco vs. Amazon S3** en lo referente a **operaciones por segundo (throughput de operaciones) y a la ruta de entrada/salida (I/O)**, fijando para ambos un mismo punto de operación de **600 ops/seg**, con el fin de:

1. Determinar **qué recursos** necesita cada solución para sostener 600 ops/seg de forma estable.
2. Cuantificar la **amplificación de I/O**: cuántas operaciones de almacenamiento "reales" genera cada operación lógica del usuario en cada plataforma.
3. Evaluar **latencia, concurrencia y headroom** (margen disponible sobre el objetivo).
4. Emitir **recomendaciones** de cuándo conviene cada arquitectura.

> ⚠️ **Aclaración metodológica.** Alfresco y S3 **no resuelven el mismo problema**. Alfresco es un **ECM** (gestión documental: metadatos, versionado, permisos finos, búsqueda full-text, flujos de trabajo); S3 es un **almacén de objetos** (durabilidad, escala y throughput sobre una API REST). Por eso la comparación "a 600 ops/seg" solo es justa si se define con precisión qué es una *operación* en cada caso. Esa definición se establece en la sección 3.1.

---

## 2. Fuentes de información relevantes

Se priorizaron **documentación oficial del fabricante**, **whitepapers de benchmark** y **mediciones empíricas independientes**.

| # | Fuente | Tipo | Dato clave aportado |
|---|--------|------|---------------------|
| 1 | AWS — *Best practices design patterns: optimizing Amazon S3 performance* (docs.aws.amazon.com) | Doc. oficial | ≥ 3.500 PUT/COPY/POST/DELETE y ≥ 5.500 GET/HEAD por segundo **por prefijo**; sin límite de prefijos |
| 2 | AWS — *Amazon S3 Announces Increased Request Rate Performance* (2018/2020) | Anuncio oficial | Confirma 3.500 escritura / 5.500 lectura por prefijo, escalado por paralelización |
| 3 | AWS — *Performance design patterns for Amazon S3* | Doc. oficial | Errores 503 *Slow Down* durante el escalado; backoff exponencial; latencias de decenas de ms en objetos < 512 KB |
| 4 | AWS — *New Amazon S3 Express One Zone* | Doc. oficial | Clase de alto rendimiento: latencia de un dígito de ms, cientos de miles de req/seg |
| 5 | dvassallo / **s3-benchmark** (GitHub) | Benchmark independiente | p90 de *time-to-first-byte* ≈ 20 ms con independencia del tamaño; ≈ 93 MB/s por hilo |
| 6 | Alfresco / Amazon — *The Alfresco ECM 1 Billion Document Benchmark on AWS & Aurora* | Whitepaper benchmark | 1.000 docs/seg en 10 nodos (≈ **100 docs/seg por nodo**); 500 usuarios Share + 200 sesiones CMIS; respuesta < 4,5 s |
| 7 | Unisys / Alfresco — *Alfresco Benchmark Report (bl100093)* | Whitepaper benchmark | 107 M documentos; **140 docs/seg**; respuesta lectura/escritura < 1 s; el *content store* fue el disco con mayor cola |
| 8 | S. O'Kennedy — *Alfresco's Billion Documents, a Closer Look* (análisis técnico) | Análisis | Confirma ≈ 100 docs/seg por nodo de repositorio; buenas prácticas de tamaño de carpeta |
| 9 | Crest Infosolutions / IBM — *Performance benchmarking of ACS on Red Hat OpenShift (Power vs x86)* | Whitepaper benchmark | Caracterización de rendimiento de ACS sobre contenedores |
| 10 | AWS re:Post — hilos sobre límites de request por prefijo y cuotas de cuenta | Soporte oficial | Existe cuota por cuenta además del límite por prefijo |

***Tabla 1.** Fuentes de información utilizadas en el estudio. **Fuente:** elaboración propia a partir de las referencias [1]–[10].*

> Las cifras de Alfresco provienen de despliegues distribuidos (repositorio + índice Solr + base de datos); las de S3, de un servicio totalmente gestionado. Esta diferencia es central en el análisis.

---

## 3. Análisis técnico

> **Nota metodológica — tres supuestos sobre los que descansan los cálculos.** Los datos de capacidad y latencia provienen de fuentes citadas (documentación oficial de AWS [1]–[4], benchmarks de Alfresco [6][7][8] y medición independiente [5]). Sobre ellos se aplican tres supuestos propios que conviene tener presentes, porque mueven los números derivados:
> 1. **Mezcla de trabajo 70 % lectura / 30 % escritura.** Es un perfil ECM típico asumido, no medido. Cambiarla altera el reparto 420/180 y, en cascada, la amplificación de I/O y el dimensionamiento de nodos.
> 2. **Factores de amplificación de I/O (≈4–7 por escritura, ≈2 por lectura).** Son estimaciones derivadas de la arquitectura de tres capas de Alfresco, no mediciones directas; por eso el resultado se expresa como rango (2,6–3,5×).
> 3. **Latencia media de Alfresco ≈ 500 ms.** Es un promedio asumido entre el "< 1 s" típico y el "< 4,5 s" del peor caso de los benchmarks. Afecta solo al cálculo de concurrencia (Tabla 5); la conclusión cualitativa (~10× más concurrencia que S3) se mantiene en todo el rango razonable.

### 3.1 Modelo de comparación: ¿qué es una "operación"?

Para comparar de forma honesta, se define una **operación lógica** como una acción de negocio del usuario, y se mide cuánta **I/O física** genera en cada plataforma.

| Operación lógica | Equivalente en S3 | Equivalente en Alfresco (ACS) |
|------------------|-------------------|-------------------------------|
| Subir un documento | 1 × `PUT` de objeto | Escritura en *content store* + transacción en BD (nodo, propiedades, ACL) + evento de indexación en Solr |
| Descargar un documento | 1 × `GET` de objeto | Lectura de metadatos/ACL en BD + lectura en *content store* |
| Actualizar metadatos | 1 × `PUT`/`COPY` (o tag) | Escrituras en BD + reindexación en Solr |
| Buscar por contenido | No nativo (requiere índice externo o S3 Select limitado) | Consulta a Solr (I/O de índice) |

***Tabla 2.** Equivalencia entre una operación lógica del usuario y la I/O que genera en cada plataforma. **Fuente:** elaboración propia a partir de la documentación de arquitectura de AWS S3 [1] y de Alfresco Content Services [6][7].*

**Mezcla de trabajo asumida** (perfil ECM típico): **70 % lecturas / 30 % escrituras**.
A 600 ops/seg → **420 lecturas/seg + 180 escrituras/seg**.

---

### 3.2 Arquitectura y ruta de I/O

La diferencia estructural es que en **S3 una operación lógica ≈ una operación de almacenamiento**, mientras que en **Alfresco una operación lógica se abre en abanico (fan-out) hacia tres subsistemas de I/O** (base de datos relacional, *content store* y motor de índice Solr).

<svg viewBox="0 0 820 470" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">
  <rect x="0" y="0" width="820" height="470" rx="10" fill="#f7f9fb"/>
  <text x="410" y="30" text-anchor="middle" font-size="18" font-weight="700" fill="#1a2b34">Ruta de I/O por operación lógica</text>
  <rect x="20" y="55" width="380" height="395" rx="10" fill="#ffffff" stroke="#2c7a6b" stroke-width="2"/>
  <text x="210" y="82" text-anchor="middle" font-size="15" font-weight="700" fill="#2c7a6b">Alfresco Content Services</text>
  <rect x="140" y="100" width="140" height="38" rx="6" fill="#2c7a6b"/>
  <text x="210" y="124" text-anchor="middle" font-size="13" fill="#ffffff">Cliente / App</text>
  <line x1="210" y1="138" x2="210" y2="165" stroke="#2c7a6b" stroke-width="2"/>
  <rect x="120" y="165" width="180" height="44" rx="6" fill="#e8f3f0" stroke="#2c7a6b"/>
  <text x="210" y="185" text-anchor="middle" font-size="12.5" font-weight="700" fill="#1a3d36">Repositorio ACS</text>
  <text x="210" y="201" text-anchor="middle" font-size="11" fill="#356b60">(N nodos · CMIS/REST)</text>
  <line x1="160" y1="209" x2="95"  y2="255" stroke="#2c7a6b" stroke-width="2"/>
  <line x1="210" y1="209" x2="210" y2="255" stroke="#2c7a6b" stroke-width="2"/>
  <line x1="260" y1="209" x2="325" y2="255" stroke="#2c7a6b" stroke-width="2"/>
  <rect x="35" y="255" width="120" height="70" rx="6" fill="#fef0e8" stroke="#d9743a"/>
  <text x="95" y="278" text-anchor="middle" font-size="11.5" font-weight="700" fill="#a8521f">Base de datos</text>
  <text x="95" y="294" text-anchor="middle" font-size="10" fill="#a8521f">metadatos · ACL</text>
  <text x="95" y="307" text-anchor="middle" font-size="10" fill="#a8521f">transacciones</text>
  <text x="95" y="319" text-anchor="middle" font-size="10" fill="#a8521f">(3–5 I/O)</text>
  <rect x="160" y="255" width="100" height="70" rx="6" fill="#eef2f7" stroke="#4a6b8a"/>
  <text x="210" y="282" text-anchor="middle" font-size="11.5" font-weight="700" fill="#33485f">Content</text>
  <text x="210" y="297" text-anchor="middle" font-size="11.5" font-weight="700" fill="#33485f">store</text>
  <text x="210" y="313" text-anchor="middle" font-size="10" fill="#33485f">(1 I/O)</text>
  <rect x="265" y="255" width="120" height="70" rx="6" fill="#f0eaf7" stroke="#7a5aa8"/>
  <text x="325" y="278" text-anchor="middle" font-size="11.5" font-weight="700" fill="#553a7a">Índice Solr</text>
  <text x="325" y="294" text-anchor="middle" font-size="10" fill="#553a7a">búsqueda</text>
  <text x="325" y="307" text-anchor="middle" font-size="10" fill="#553a7a">full-text</text>
  <text x="325" y="319" text-anchor="middle" font-size="10" fill="#553a7a">(1 I/O)</text>
  <rect x="60" y="360" width="300" height="70" rx="8" fill="#fff6f3" stroke="#d9743a" stroke-dasharray="4 3"/>
  <text x="210" y="385" text-anchor="middle" font-size="13" font-weight="700" fill="#a8521f">1 escritura lógica  →  ≈ 4–7 I/O backend</text>
  <text x="210" y="408" text-anchor="middle" font-size="11" fill="#a8521f">Amplificación de I/O elevada</text>
  <rect x="420" y="55" width="380" height="395" rx="10" fill="#ffffff" stroke="#e07c1f" stroke-width="2"/>
  <text x="610" y="82" text-anchor="middle" font-size="15" font-weight="700" fill="#e07c1f">Amazon S3</text>
  <rect x="540" y="100" width="140" height="38" rx="6" fill="#e07c1f"/>
  <text x="610" y="124" text-anchor="middle" font-size="13" fill="#ffffff">Cliente / App</text>
  <line x1="610" y1="138" x2="610" y2="170" stroke="#e07c1f" stroke-width="2"/>
  <rect x="510" y="170" width="200" height="44" rx="6" fill="#fdefe0" stroke="#e07c1f"/>
  <text x="610" y="190" text-anchor="middle" font-size="12.5" font-weight="700" fill="#9c5510">API REST HTTPS</text>
  <text x="610" y="206" text-anchor="middle" font-size="11" fill="#b56a23">(PUT / GET / HEAD)</text>
  <line x1="610" y1="214" x2="610" y2="255" stroke="#e07c1f" stroke-width="2"/>
  <rect x="500" y="255" width="220" height="70" rx="6" fill="#fdefe0" stroke="#e07c1f"/>
  <text x="610" y="280" text-anchor="middle" font-size="12.5" font-weight="700" fill="#9c5510">Almacenamiento de objetos</text>
  <text x="610" y="298" text-anchor="middle" font-size="10.5" fill="#b56a23">prefijos · gestionado · auto-escalado</text>
  <text x="610" y="313" text-anchor="middle" font-size="10.5" fill="#b56a23">(replicación interna transparente)</text>
  <rect x="460" y="360" width="300" height="70" rx="8" fill="#fff8f0" stroke="#e07c1f" stroke-dasharray="4 3"/>
  <text x="610" y="385" text-anchor="middle" font-size="13" font-weight="700" fill="#9c5510">1 escritura lógica  →  ≈ 1 I/O backend</text>
  <text x="610" y="408" text-anchor="middle" font-size="11" fill="#9c5510">Amplificación de I/O ≈ 1 (gestionada)</text>
</svg>

***Figura 1.** Ruta de I/O por operación lógica: fan-out de Alfresco hacia tres subsistemas frente a la operación plana de S3. **Fuente:** elaboración propia a partir de la arquitectura de Alfresco Content Services [6][7][8] y de la documentación de Amazon S3 [1].*

**Lectura del diagrama:** en Alfresco, cada subida obliga a coordinar tres almacenes distintos (cada uno con su propio I/O, su propio cuello de botella y su propia escala). En el benchmark de Unisys, el disco con mayor profundidad de cola fue precisamente el **content store** [7]. En S3 esa coordinación es interna al servicio y transparente para la aplicación.

---

### 3.3 Capacidad y *headroom* a 600 ops/seg

#### Amazon S3 — el objetivo cabe en un solo prefijo

Los límites publicados por AWS son **≥ 3.500 escrituras/seg** y **≥ 5.500 lecturas/seg por prefijo**, sin límite en el número de prefijos [1][2]. Con la mezcla asumida (180 escrituras + 420 lecturas):

- Escrituras: 180 / 3.500 = **5,1 %** de la capacidad de **un** prefijo → *headroom* ≈ **19×**.
- Lecturas: 420 / 5.500 = **7,6 %** de la capacidad de **un** prefijo → *headroom* ≈ **13×**.

<svg viewBox="0 0 820 320" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">
  <rect x="0" y="0" width="820" height="320" rx="10" fill="#f7f9fb"/>
  <text x="410" y="30" text-anchor="middle" font-size="16" font-weight="700" fill="#1a2b34">S3: carga a 600 ops/seg frente al límite de UN prefijo</text>
  <line x1="170" y1="270" x2="780" y2="270" stroke="#cdd6dd" stroke-width="1.5"/>
  <text x="160" y="120" text-anchor="end" font-size="12" font-weight="700" fill="#33485f">Escritura</text>
  <rect x="170" y="100" width="382" height="32" rx="4" fill="#fde6cf" stroke="#e07c1f"/>
  <text x="556" y="120" font-size="11" fill="#9c5510">límite ≥ 3.500/seg por prefijo</text>
  <rect x="170" y="100" width="20" height="32" rx="4" fill="#e07c1f"/>
  <text x="196" y="121" font-size="11" font-weight="700" fill="#9c5510">180/seg</text>
  <text x="160" y="200" text-anchor="end" font-size="12" font-weight="700" fill="#33485f">Lectura</text>
  <rect x="170" y="180" width="600" height="32" rx="4" fill="#fde6cf" stroke="#e07c1f"/>
  <text x="470" y="200" font-size="11" fill="#9c5510" text-anchor="middle">límite ≥ 5.500/seg por prefijo</text>
  <rect x="170" y="180" width="46" height="32" rx="4" fill="#e07c1f"/>
  <text x="222" y="201" font-size="11" font-weight="700" fill="#9c5510">420/seg</text>
  <text x="410" y="258" text-anchor="middle" font-size="12" fill="#356b60" font-weight="700">A 600 ops/seg se usa el 5–8 % de un único prefijo: ~13–19× de margen, sin diseño especial</text>
</svg>

***Figura 2.** Carga de 600 ops/seg (180 escrituras + 420 lecturas) frente al límite de un único prefijo de S3. **Fuente:** límites de 3.500 escr./5.500 lect. por prefijo de la documentación oficial de AWS [1][2]; cálculo de porcentajes y headroom de elaboración propia.*

#### Alfresco — el objetivo requiere dimensionar un clúster

Los benchmarks sitúan el rendimiento de **un nodo de repositorio** en torno a **~100 docs/seg** (1.000 docs/seg en 10 nodos en el benchmark de 1.000 M de documentos sobre AWS/Aurora [6]) y hasta **140 docs/seg** en el benchmark de Unisys sobre un único servidor [7]. Las escrituras son más caras que las lecturas por la amplificación de I/O.

Dimensionamiento estimado para **600 ops/seg** (cifras orientativas derivadas de [6][7][8]):

> **Sobre el rango de nodos.** Las tasas de benchmark (100–140 docs/seg por nodo) son de **ingesta (escritura)**. Si se tratan como ops mixtas directas, el resultado conservador es 600 ÷ 100 = **6 nodos** a 600 ÷ 140 ≈ **5 nodos**. Solo bajo un modelo de "presupuesto de I/O" (donde las lecturas, ≈2 I/O, cuestan menos que las escrituras, ≈5 I/O) y con la mezcla 70/30, la capacidad mixta por nodo sube a ~172 ops/seg y bastarían **4 nodos**. Por eso el límite inferior de 4 es optimista y se reserva para cargas muy intensivas en lectura.

| Capa | Métrica de referencia | Necesidad estimada a 600 ops/seg |
|------|-----------------------|----------------------------------|
| Repositorio ACS | ~100–140 ops/seg por nodo | **5–6 nodos** (4 solo si la carga es muy intensiva en lectura) |
| Motor de índice (Solr) | indexación > 2.000 docs/seg con *sharding* [6] | 1+ *shard*; *sharding* recomendado a escala |
| Base de datos | el cuello frecuente en escritura | Instancia con IOPS provisionados / Aurora |
| Content store | disco con mayor cola en pruebas [7] | Almacenamiento con IOPS dedicados |

***Tabla 3.** Dimensionamiento estimado por capa para sostener 600 ops/seg en Alfresco. **Fuente:** métricas de referencia de los benchmarks [6][7][8]; estimación de necesidades de elaboración propia.*

<svg viewBox="0 0 820 300" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">
  <rect x="0" y="0" width="820" height="300" rx="10" fill="#f7f9fb"/>
  <text x="410" y="30" text-anchor="middle" font-size="16" font-weight="700" fill="#1a2b34">Alfresco: nodos de repositorio para alcanzar 600 ops/seg</text>
  <line x1="120" y1="250" x2="780" y2="250" stroke="#cdd6dd" stroke-width="1.5"/>
  <line x1="120" y1="80"  x2="780" y2="80"  stroke="#d9743a" stroke-width="1.5" stroke-dasharray="6 4"/>
  <text x="775" y="74" text-anchor="end" font-size="11" font-weight="700" fill="#a8521f">objetivo 600 ops/seg</text>
  <g>
    <rect x="170" y="219" width="70" height="31" fill="#2c7a6b"/>
    <text x="205" y="270" text-anchor="middle" font-size="11" fill="#33485f">1 nodo</text>
    <text x="205" y="212" text-anchor="middle" font-size="10" fill="#2c7a6b">110</text>
  </g>
  <g>
    <rect x="330" y="156" width="70" height="94" fill="#2c7a6b"/>
    <text x="365" y="270" text-anchor="middle" font-size="11" fill="#33485f">3 nodos</text>
    <text x="365" y="149" text-anchor="middle" font-size="10" fill="#2c7a6b">330</text>
  </g>
  <g>
    <rect x="490" y="94" width="70" height="156" fill="#2c7a6b"/>
    <text x="525" y="270" text-anchor="middle" font-size="11" fill="#33485f">5 nodos</text>
    <text x="525" y="87" text-anchor="middle" font-size="10" fill="#2c7a6b">550</text>
  </g>
  <g>
    <rect x="650" y="63" width="70" height="187" fill="#1f5e52"/>
    <text x="685" y="270" text-anchor="middle" font-size="11" fill="#33485f">6 nodos</text>
    <text x="685" y="56" text-anchor="middle" font-size="10" font-weight="700" fill="#1f5e52">660 ✓</text>
  </g>
  <text x="125" y="255" text-anchor="end" font-size="10" fill="#7c8a93">ops/seg</text>
</svg>

***Figura 3.** Capacidad acumulada al añadir nodos de repositorio Alfresco (≈ 110 ops/seg por nodo) hasta superar el objetivo de 600 ops/seg. **Fuente:** rendimiento por nodo derivado de los benchmarks de Alfresco [6][7]; proyección lineal de elaboración propia.*

> **Conclusión de capacidad:** S3 sostiene 600 ops/seg **sin diseño adicional** (un solo prefijo, servicio gestionado). Alfresco sostiene 600 ops/seg pero **requiere dimensionar y operar 3 capas** (repositorio, índice, base de datos) con redundancia.

---

### 3.4 Amplificación de I/O

La métrica más reveladora a igual carga de **600 ops/seg lógicas** es cuánta **I/O física** se genera realmente en el backend.

| Plataforma | I/O por escritura | I/O por lectura | I/O física total estimada a 600 ops/seg (180 E / 420 L) |
|-----------|-------------------|-----------------|---------------------------------------------------------|
| **Amazon S3** | ≈ 1 | ≈ 1 | **≈ 600 ops** de almacenamiento (gestionadas/transparentes) |
| **Alfresco** | ≈ 4–7 (BD + content store + Solr) | ≈ 2 (BD + content store) | **≈ 1.560–2.100 I/O** (2,9× central) repartidas en 3 subsistemas |

***Tabla 4.** Amplificación de I/O: I/O física generada por 600 ops/seg lógicas en cada plataforma. **Fuente:** factor ≈1 de S3 según su modelo de objetos [1]; factores de Alfresco estimados a partir de su arquitectura de tres capas [6][7][8] (el content store fue el disco con mayor cola en [7]). Cálculo de elaboración propia.*

> **Detalle del rango (Alfresco).** Con el factor central (5 por escritura, 2 por lectura): 180×5 + 420×2 = 900 + 840 = **1.740 I/O → 2,9×**. Extremo bajo (4 escr./2 lect.): 720 + 840 = 1.560 → **2,6×**. Extremo alto (7 escr./2 lect.): 1.260 + 840 = 2.100 → **3,5×**. El "≈1" de S3 es la I/O *gestionada por la aplicación*: internamente S3 replica cada objeto en ≥3 zonas de disponibilidad, pero de forma transparente y sin coste operativo para el usuario.

<svg viewBox="0 0 820 270" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">
  <rect x="0" y="0" width="820" height="270" rx="10" fill="#f7f9fb"/>
  <text x="410" y="30" text-anchor="middle" font-size="16" font-weight="700" fill="#1a2b34">I/O física generada por 600 ops/seg lógicas (180 escrituras + 420 lecturas)</text>
  <line x1="180" y1="220" x2="780" y2="220" stroke="#cdd6dd" stroke-width="1.5"/>
  <text x="170" y="95" text-anchor="end" font-size="12" font-weight="700" fill="#9c5510">S3</text>
  <rect x="180" y="78" width="193" height="34" rx="4" fill="#e07c1f"/>
  <text x="383" y="100" font-size="12" font-weight="700" fill="#9c5510">≈ 600 I/O</text>
  <text x="170" y="165" text-anchor="end" font-size="12" font-weight="700" fill="#2c7a6b">Alfresco</text>
  <rect x="180" y="148" width="290" height="34" fill="#d9743a"/>
  <text x="325" y="170" text-anchor="middle" font-size="11" fill="#ffffff">BD ~900</text>
  <rect x="470" y="148" width="193" height="34" fill="#4a6b8a"/>
  <text x="566" y="170" text-anchor="middle" font-size="11" fill="#ffffff">Content ~600</text>
  <rect x="663" y="148" width="58" height="34" fill="#7a5aa8"/>
  <text x="732" y="170" font-size="11" font-weight="700" fill="#553a7a">+Solr</text>
  <text x="450" y="245" text-anchor="middle" font-size="12.5" font-weight="700" fill="#a8521f">Alfresco ≈ 1.560–2.100 I/O totales  ·  ~2,6–3,5× la I/O de S3 (2,9× central)</text>
</svg>

***Figura 4.** I/O física generada por 600 ops/seg lógicas, desglosada por subsistema en Alfresco. **Fuente:** misma base de cálculo que la Tabla 4 (modelo S3 [1]; arquitectura de Alfresco [6][7][8]); elaboración propia.*

Esta amplificación es la causa de que Alfresco necesite **almacenamiento con IOPS dedicados** para la base de datos y el content store, mientras que S3 absorbe la misma carga lógica de forma plana.

---

### 3.5 Latencia y concurrencia

**Latencia observada:**

- **S3:** la guía oficial de AWS cita latencias de objeto pequeño de ~100–200 ms para *first-byte* [3]; las mediciones empíricas independientes muestran un **p90 de *time-to-first-byte* ≈ 20 ms** con independencia del tamaño del objeto, y ~93 MB/s por hilo [5]. La clase **S3 Express One Zone** baja a latencias de **un dígito de ms** [4].
- **Alfresco:** el benchmark de Unisys reporta lectura/escritura **< 1 s** [7]; el benchmark de 1.000 M documentos reporta **< 4,5 s** incluso para las operaciones más largas con 500 usuarios Share + 200 sesiones CMIS [6].

<svg viewBox="0 0 820 300" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">
  <rect x="0" y="0" width="820" height="300" rx="10" fill="#f7f9fb"/>
  <text x="410" y="30" text-anchor="middle" font-size="16" font-weight="700" fill="#1a2b34">Latencia por operación (escala logarítmica, ms)</text>
  <line x1="210" y1="250" x2="780" y2="250" stroke="#cdd6dd" stroke-width="1.5"/>
  <text x="210" y="268" text-anchor="middle" font-size="9" fill="#7c8a93">10</text>
  <text x="400" y="268" text-anchor="middle" font-size="9" fill="#7c8a93">100</text>
  <text x="590" y="268" text-anchor="middle" font-size="9" fill="#7c8a93">1.000</text>
  <text x="755" y="268" text-anchor="middle" font-size="9" fill="#7c8a93">~4.500</text>
  <text x="200" y="78" text-anchor="end" font-size="11" font-weight="700" fill="#9c5510">S3 Express</text>
  <rect x="210" y="62" width="36" height="26" rx="3" fill="#f0a050"/>
  <text x="252" y="80" font-size="10" fill="#9c5510">~5 ms</text>
  <text x="200" y="118" text-anchor="end" font-size="11" font-weight="700" fill="#9c5510">S3 p90 TTFB</text>
  <rect x="210" y="102" width="62" height="26" rx="3" fill="#e07c1f"/>
  <text x="278" y="120" font-size="10" fill="#9c5510">~20 ms</text>
  <text x="200" y="158" text-anchor="end" font-size="11" font-weight="700" fill="#9c5510">S3 (guía AWS)</text>
  <rect x="210" y="142" width="200" height="26" rx="3" fill="#f4b870"/>
  <text x="416" y="160" font-size="10" fill="#9c5510">100–200 ms</text>
  <text x="200" y="198" text-anchor="end" font-size="11" font-weight="700" fill="#2c7a6b">Alfresco L/E</text>
  <rect x="210" y="182" width="380" height="26" rx="3" fill="#2c7a6b"/>
  <text x="596" y="200" font-size="10" fill="#2c7a6b">&lt; 1.000 ms</text>
  <text x="200" y="238" text-anchor="end" font-size="11" font-weight="700" fill="#2c7a6b">Alfresco compleja</text>
  <rect x="210" y="222" width="545" height="26" rx="3" fill="#1f5e52"/>
  <text x="755" y="240" font-size="10" fill="#ffffff" text-anchor="end">&lt; 4.500 ms</text>
</svg>

***Figura 5.** Latencia por operación en escala logarítmica. **Fuente:** S3 Express y guía de 100–200 ms de la documentación oficial de AWS [3][4]; p90 TTFB ≈ 20 ms del benchmark independiente s3-benchmark [5]; latencias de Alfresco (< 1 s y < 4,5 s) de los benchmarks [6][7].*

**Concurrencia necesaria (Ley de Little: `concurrencia = throughput × latencia`):**

| Plataforma | Latencia media usada | Concurrencia para 600 ops/seg |
|-----------|----------------------|-------------------------------|
| S3 (p90 TTFB ~20–50 ms) | 0,05 s | 600 × 0,05 = **~30 conexiones** en vuelo |
| S3 (guía 100–200 ms) | 0,15 s | 600 × 0,15 = **~90 conexiones** |
| Alfresco (~500 ms media) | 0,50 s | 600 × 0,50 = **~300 operaciones** en vuelo |

***Tabla 5.** Concurrencia en vuelo necesaria para sostener 600 ops/seg según la Ley de Little. **Fuente:** latencias de S3 [3][5] y de Alfresco [6][7]; aplicación de la Ley de Little (concurrencia = throughput × latencia) de elaboración propia.*

> A igual objetivo de 600 ops/seg, Alfresco debe sostener **~10× más operaciones concurrentes en vuelo** que S3 por su mayor latencia por operación, lo que se traduce en mayores *thread pools*, conexiones de BD y memoria.

---

### 3.6 Tabla resumen comparativa (a 600 ops/seg)

| Dimensión | Amazon S3 | Alfresco Content Services |
|-----------|-----------|---------------------------|
| Capacidad nominal | ≥ 3.500 escr. / ≥ 5.500 lect. **por prefijo** [1] | ~100–140 ops/seg **por nodo** [6][7] |
| Recursos para 600 ops/seg | 1 prefijo (5–8 % de uso) | 5–6 nodos repo + Solr + BD con IOPS |
| *Headroom* a 600 ops/seg | ~13–19× | Ajustado; escala añadiendo nodos/*shards* |
| Amplificación de I/O | ≈ 1× | ≈ 4–7× (escritura) / ≈ 2× (lectura) |
| Latencia típica | ~20 ms p90 [5]; 100–200 ms guía [3] | < 1 s; hasta 4,5 s en operaciones complejas [6][7] |
| Concurrencia a 600 ops/seg | ~30–90 conexiones | ~300 operaciones en vuelo |
| Operación bajo carga | Auto-escalado; 503 *Slow Down* temporales [3] | Requiere *sharding* de Solr y tuning de BD [6] |
| Búsqueda full-text | No nativa | Nativa (Solr) |
| Metadatos / permisos finos / versionado | Limitado (tags, ACL de objeto) | Nativo y rico |
| Modelo operativo | Totalmente gestionado (serverless) | Autogestionado (3 capas con estado) |

***Tabla 6.** Resumen comparativo Alfresco vs. Amazon S3 a 600 ops/seg. **Fuente:** consolidación de las secciones 3.1–3.5; datos de S3 [1][3][5] y de Alfresco [6][7] referenciados por celda.*

---

## 4. Recomendaciones

1. **Si el requisito es exclusivamente throughput de almacenamiento a 600 ops/seg → Amazon S3.** El objetivo cabe holgadamente en un único prefijo (5–8 % de su capacidad, ~13–19× de margen) [1][2], con amplificación de I/O ≈ 1 y sin necesidad de dimensionar ni operar infraestructura con estado. Es la opción de menor latencia, menor complejidad operativa y mayor *headroom*.

2. **Si el requisito incluye capacidades ECM (búsqueda full-text, metadatos ricos, versionado, permisos finos, flujos de trabajo) → Alfresco**, aceptando que sostener 600 ops/seg implica **5–6 nodos de repositorio + Solr + base de datos con IOPS provisionados** y una **amplificación de I/O de ~2,6–3,5× (≈2,9× central)** sobre la carga lógica. Conviene presupuestar almacenamiento de alto IOPS para *content store* y base de datos, ya que son los cuellos de botella observados en benchmark [7].

3. **Arquitectura híbrida (recomendada en la mayoría de casos reales).** Usar **Alfresco como capa de gestión documental** (metadatos, búsqueda, permisos, flujos) y **S3 como *content store* subyacente**. Alfresco soporta almacenes de contenido sobre S3, de modo que la I/O pesada de objetos la absorbe S3 (amplificación ≈ 1 en esa capa) mientras Alfresco conserva las funciones de ECM. Esto reduce la presión de IOPS sobre disco local y aprovecha el auto-escalado de S3.

4. **Dimensionar con margen y por capa.** Para Alfresco, no basta con sumar nodos de repositorio: a 600 ops/seg el límite suele aparecer en **base de datos** y **content store** por la amplificación de I/O. Aplicar ***sharding* de Solr** desde el diseño [6][8] y limitar el número de documentos por carpeta (buena práctica documentada) [7][8].

5. **Para S3, planificar el escalado gradual.** Aunque 600 ops/seg es trivial, ante picos súbitos pueden aparecer respuestas **503 *Slow Down*** mientras el servicio escala; implementar **reintentos con backoff exponencial** y, si se requieren latencias de un dígito de ms, evaluar **S3 Express One Zone** [3][4].

6. **Validar con un benchmark propio.** Las cifras por nodo de Alfresco (~100–140 ops/seg) y de latencia de S3 (~20 ms p90) dependen de la mezcla de operaciones, tamaño de objeto, región y configuración [5][9]. Antes de fijar el dimensionamiento definitivo, ejecutar una prueba de carga con el perfil real (70/30 u otro) y los tamaños de fichero reales.

---

## Referencias

1. AWS — *Best practices design patterns: optimizing Amazon S3 performance*. https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance.html
2. AWS — *Amazon S3 Announces Increased Request Rate Performance*. https://aws.amazon.com/about-aws/whats-new/2018/07/amazon-s3-announces-increased-request-rate-performance/
3. AWS — *Performance design patterns for Amazon S3*. https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance-design-patterns.html
4. AWS — *New Amazon S3 Express One Zone high performance storage class*. https://aws.amazon.com/blogs/aws/new-amazon-s3-express-one-zone-high-performance-storage-class/
5. D. Vassallo — *s3-benchmark* (medición independiente de latencia/throughput). https://github.com/dvassallo/s3-benchmark
6. Alfresco / Amazon — *The Alfresco ECM 1 Billion Document Benchmark on AWS and Aurora*. https://www.slideshare.net/slideshow/the-alfresco-ecm-1-billion-document-benchmark-on-aws-and-aurora-benchmark-details-and-scalability-recommendations/54444004
7. Unisys / Alfresco — *Alfresco Benchmark Report (bl100093)*. https://www.slideshare.net/slideshow/alfresco-benchmark-reportbl100093/5869700
8. S. O'Kennedy — *Alfresco's Billion Documents – a Closer Look*. https://www.linkedin.com/pulse/alfrescos-billion-documents-closer-look-steven-o-kennedy
9. Crest Infosolutions / IBM — *Performance benchmarking of Alfresco Content Services (ACS) on Red Hat OpenShift on IBM Power vs x86*. https://crestsolution.com/resources/whitepapers/performance-benchmarking-of-alfresco-content-services-acs-on-red-hat-openshift-on-ibm-power-vs-x86/
10. AWS re:Post — *Understanding reading rate limit from a single prefix in S3* / *What's the max rate limit of s3 bucket access?*. https://repost.aws/questions/QUM5pQi20uSWK3lWoCH34W5w/understanding-reading-rate-limit-from-a-single-prefix-in-s3

---

*Nota: las cifras de dimensionamiento de Alfresco (nodos para 600 ops/seg) y los factores de amplificación de I/O son estimaciones de ingeniería derivadas de los benchmarks citados y de la arquitectura de tres capas de ACS; deben validarse con una prueba de carga sobre el perfil de operaciones real antes de un diseño definitivo.*