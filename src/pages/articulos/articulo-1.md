---
layout: ../../layouts/ArticleLayout.astro
title: "Investigación: Solución basada en Alfresco vs. solución basada en Amazon S3 (a 600 ops/seg)"
description: "Comparativa técnica de operaciones por segundo e I/O entre Alfresco Content Services y Amazon S3, tomando como referencia común 600 ops/seg."
date: "2026-06-24"
---

> **Alcance del estudio:** **comparativa técnica** de **operaciones por segundo (ops/seg) e I/O** entre una arquitectura de gestión documental basada en **Alfresco Content Services (ACS)** y una arquitectura de almacenamiento de objetos basada en **Amazon S3**, tomando como punto de referencia común un objetivo de **600 operaciones por segundo**. El propósito es **comparar y decidir**; el dimensionamiento que aquí se ofrece es **orientativo** y **no pretende sustituir un ejercicio de *sizing* de producción**.
> **Fecha:** junio 2026 · **Tipo:** análisis técnico con datos numéricos y referencias.

---

## 1. Objetivo

Analizar y comparar **Alfresco vs. Amazon S3** en lo referente a **operaciones por segundo (throughput de operaciones) y a la ruta de entrada/salida (I/O)**, fijando para ambos un mismo punto de operación de **600 ops/seg**, con el fin de:

1. Determinar **qué recursos** necesita cada solución para sostener 600 ops/seg de forma estable.
2. Cuantificar la **amplificación de I/O**: cuántas operaciones de almacenamiento "reales" genera cada operación lógica del usuario en cada plataforma.
3. Evaluar **latencia, concurrencia y headroom** (margen disponible sobre el objetivo).
4. Emitir **recomendaciones** de cuándo conviene cada arquitectura.

> Nota: Alfresco y S3 **no resuelven el mismo problema**. Alfresco es un **ECM** (gestión documental: metadatos, versionado, permisos finos, búsqueda full-text, flujos de trabajo); S3 es un **almacén de objetos** (durabilidad, escala y throughput sobre una API REST). Por eso la comparación "a 600 ops/seg" solo es justa si se define con precisión qué es una *operación* en cada caso. Esa definición se establece en la sección 3.1.

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
| 6 | Alfresco / Amazon — *The Alfresco ECM 1 Billion Document Benchmark on AWS & Aurora* **(oct. 2015, Alfresco One 5.1)** | Whitepaper benchmark | 1.000 docs/seg en 10 nodos (≈ **100 docs/seg por nodo**); 500 usuarios Share + 200 sesiones CMIS; respuesta < 4,5 s |
| 7 | Unisys / Alfresco — *Alfresco Benchmark Report (bl100093)* **(2007, Alfresco 2.2)** | Whitepaper benchmark | ~100 M documentos; **140 docs/seg**; respuesta lectura/escritura < 1 s; el *content store* fue el disco con mayor cola |
| 8 | S. O'Kennedy — *Alfresco's Billion Documents, a Closer Look* **(2018, analiza el benchmark de 2015)** | Análisis | Confirma ≈ 100 docs/seg por nodo de repositorio; buenas prácticas de tamaño de carpeta |
| 9 | Crest Infosolutions / IBM — *Performance benchmarking of ACS on Red Hat OpenShift (Power vs x86)* | Whitepaper benchmark | Caracterización de rendimiento de ACS sobre contenedores |
| 10 | AWS re:Post — hilos sobre límites de request por prefijo y cuotas de cuenta | Soporte oficial | Existe cuota por cuenta además del límite por prefijo |
| 11 | T. de la Fuente / Alfresco — *Sizing your Alfresco Platform* | Guía del fabricante | Modelo de capacidad por operación: cada operación pesa y toca capas distintas (escritura → Repo·Solr·BD; descarga → Repo) |
| 12 | Alfresco / Hyland — *Set up clustering* (documentación oficial vigente) | Doc. oficial (actual) | El escalado actual sigue siendo horizontal: *clustering* para alta concurrencia/throughput, un componente por nodo, Solr y BD separados |
| 13 | Alfresco / Hyland — *What's new* (ACS 23.1+) y notas de versión ACS 25.x/26.x | Doc. oficial (actual) | Producto vigente sobre *stack* moderno: Solr 9, Java 17, Tomcat 10, Spring 6, contenedores ARM64, despliegue Kubernetes/Helm |

***Tabla 1.** Fuentes de información utilizadas en el estudio. **Fuente:** elaboración propia a partir de las referencias [1]–[13].*

> Las cifras de Alfresco provienen de despliegues distribuidos (repositorio + índice Solr + base de datos); las de S3, de un servicio totalmente gestionado. Esta diferencia es central en el análisis.
>
> **Nota sobre las fuentes de Alfresco.** La tasa de throughput por nodo (≈100–140 docs/seg) procede de los benchmarks públicos de referencia [6][7] y sigue siendo el dato numérico publicado más citable. Lo relevante es que la **arquitectura que esos benchmarks describen no ha cambiado** y está **vigente en la documentación oficial actual** de Alfresco/Hyland: el escalado sigue siendo horizontal —*clustering* para alta concurrencia/throughput, índice Solr con *sharding* y base de datos transaccional separada— tal como recoge la guía de clustering vigente [12], sobre un *stack* moderno (ACS 25.x/26.x, Solr 9, Java 17, Tomcat 10, despliegue en Kubernetes/Helm) [13], y ACS se sigue *benchmarkeando* sobre infraestructura actual (Red Hat OpenShift en Power10/x86, 2024) [9]. Como el rendimiento por nodo del hardware actual (NVMe, CPU modernas, Aurora/PostgreSQL recientes) es muy superior al de 2007/2015, el dimensionamiento de este artículo es **conservador**: un despliegue moderno sostendría 600 ops/seg con **igual o menos** infraestructura que la aquí estimada.

---

## 3. Análisis técnico

> **Nota metodológica — qué es dato y qué es estimación.** La mayor parte de la comparación descansa en **datos con fuente**: los topes de S3 (3.500/5.500 por prefijo [1][2]), las latencias de S3 (~20 ms p90 [5]; 100–200 ms [3]), las tasas por nodo de Alfresco (100–140 docs/seg [6][7]) y sus latencias (< 1 s a < 4,5 s [6][7]). Las **conclusiones cualitativas del artículo no dependen de ningún supuesto** y se sostienen solo con esos hechos.
> Sobre ellos hay **una única estimación propia** que conviene distinguir claramente, porque no es una medición:
> - **Factores de amplificación de I/O de Alfresco (≈4–7 por escritura, ≈2 por lectura).** Se derivan de la semántica documentada de cada operación (una escritura toca content store + varias filas de BD + un evento Solr), pero **no están medidos**. Por eso, allí donde aparecen (Tabla 4, Figura 4) van marcados como **"(estimado)"** y deben leerse como **escenario ilustrativo**, no como dato al nivel de los 3.500/5.500 de AWS.
>
> No se asume ninguna latencia media inventada: la concurrencia (Tabla 5) se calcula con el **rango de latencia con fuente** de cada plataforma.

### 3.1 Modelo de comparación: ¿qué es una "operación"?

Para comparar de forma honesta, se define una **operación lógica** como una acción de negocio del usuario, y se mide cuánta **I/O física** genera en cada plataforma.

| Operación lógica | Equivalente en S3 | Equivalente en Alfresco (ACS) |
|------------------|-------------------|-------------------------------|
| Subir un documento | 1 × `PUT` de objeto | Escritura en *content store* + transacción en BD (nodo, propiedades, ACL) + evento de indexación en Solr |
| Descargar un documento | 1 × `GET` de objeto | Lectura de metadatos/ACL en BD + lectura en *content store* |
| Actualizar metadatos | 1 × `PUT`/`COPY` (o tag) | Escrituras en BD + reindexación en Solr |
| Buscar por contenido | No nativo (requiere índice externo o S3 Select limitado) | Consulta a Solr (I/O de índice) |

***Tabla 2.** Equivalencia entre una operación lógica del usuario y la I/O que genera en cada plataforma. **Fuente:** elaboración propia a partir de la documentación de arquitectura de AWS S3 [1] y de Alfresco Content Services [6][7].*

El reparto entre lecturas y escrituras se trata de forma **genérica**: como se verá, las conclusiones de capacidad y de I/O se sostienen para **cualquier mezcla** lectura/escritura, por lo que no se fija un perfil concreto.

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
  <text x="210" y="385" text-anchor="middle" font-size="13" font-weight="700" fill="#a8521f">1 escritura lógica  →  ≈ 4–7 I/O backend (est.)</text>
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

Los límites publicados por AWS son **≥ 3.500 escrituras/seg** y **≥ 5.500 lecturas/seg por prefijo**, sin límite en el número de prefijos [1][2]. Como lectura y escritura tienen **topes separados que no compiten entre sí**, basta examinar los dos casos extremos para acotar el resultado **bajo cualquier mezcla**:

- Caso peor (las 600 fueran **todo escrituras**): 600 / 3.500 = **17 %** de un prefijo → *headroom* ≈ **5,8×**.
- Caso mejor (las 600 fueran **todo lecturas**): 600 / 5.500 = **11 %** de un prefijo → *headroom* ≈ **9,2×**.

Es decir, **con cualquier reparto lectura/escritura, 600 ops/seg ocupan entre el 11 % y el 17 % de un único prefijo** y dejan **≥ 5,8× de margen**.

<svg viewBox="0 0 820 320" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">
  <rect x="0" y="0" width="820" height="320" rx="10" fill="#f7f9fb"/>
  <text x="410" y="30" text-anchor="middle" font-size="16" font-weight="700" fill="#1a2b34">S3: 600 ops/seg frente al límite de UN prefijo (cualquier mezcla)</text>
  <line x1="200" y1="270" x2="780" y2="270" stroke="#cdd6dd" stroke-width="1.5"/>
  <text x="190" y="120" text-anchor="end" font-size="12" font-weight="700" fill="#33485f">Todo escritura</text>
  <rect x="200" y="100" width="560" height="32" rx="4" fill="#fde6cf" stroke="#e07c1f"/>
  <text x="650" y="120" font-size="11" fill="#9c5510">límite ≥ 3.500/seg</text>
  <rect x="200" y="100" width="96" height="32" rx="4" fill="#e07c1f"/>
  <text x="306" y="121" font-size="11" font-weight="700" fill="#9c5510">600/seg = 17 %</text>
  <text x="190" y="200" text-anchor="end" font-size="12" font-weight="700" fill="#33485f">Todo lectura</text>
  <rect x="200" y="180" width="560" height="32" rx="4" fill="#fde6cf" stroke="#e07c1f"/>
  <text x="650" y="200" font-size="11" fill="#9c5510">límite ≥ 5.500/seg</text>
  <rect x="200" y="180" width="61" height="32" rx="4" fill="#e07c1f"/>
  <text x="271" y="201" font-size="11" font-weight="700" fill="#9c5510">600/seg = 11 %</text>
  <text x="410" y="255" text-anchor="middle" font-size="12" fill="#356b60" font-weight="700">Bajo cualquier reparto: 11–17 % de un único prefijo · headroom ≥ 5,8× · sin diseño especial</text>
</svg>

***Figura 2.** Carga de 600 ops/seg frente al límite de un único prefijo de S3, en los dos casos extremos (todo escritura y todo lectura). **Fuente:** límites de 3.500 escr./5.500 lect. por prefijo de la documentación oficial de AWS [1][2]; porcentajes y headroom de elaboración propia. La conclusión es robusta a cualquier mezcla.*

#### Alfresco — el objetivo requiere dimensionar un clúster

Los benchmarks sitúan el rendimiento de **un nodo de repositorio** en torno a **~100 docs/seg** (1.000 docs/seg en 10 nodos en el benchmark de 1.000 M de documentos sobre AWS/Aurora [6]) y hasta **140 docs/seg** en el benchmark de Unisys sobre un único servidor [7]. Las escrituras son más caras que las lecturas por la amplificación de I/O.

Dimensionamiento estimado para **600 ops/seg** (cifras orientativas derivadas de [6][7][8]):

> **Sobre el rango de nodos.** Las tasas de benchmark (100–140 docs/seg por nodo) son de **ingesta (escritura)**, el caso más costoso. Tratándolas directamente como capacidad por nodo, el objetivo de 600 ops/seg sale de dividir: 600 ÷ 140 ≈ **5 nodos** (extremo favorable) a 600 ÷ 100 = **6 nodos** (extremo conservador). De ahí el **rango de referencia de 5–6 nodos**. Como las lecturas son más baratas que las escrituras, una carga con predominio de lectura tiende al extremo inferior del rango.

| Capa | Métrica de referencia | Necesidad estimada a 600 ops/seg |
|------|-----------------------|----------------------------------|
| Repositorio ACS | ~100–140 ops/seg por nodo | **5–6 nodos** |
| Motor de índice (Solr) | indexación > 2.000 docs/seg con *sharding* [6] | 1+ *shard*; *sharding* recomendado a escala |
| Base de datos | el cuello frecuente en escritura | Instancia con IOPS provisionados / Aurora |
| Content store | disco con mayor cola en pruebas [7] | Almacenamiento con IOPS dedicados |

***Tabla 3.** Dimensionamiento estimado por capa para sostener 600 ops/seg en Alfresco. **Fuente:** métricas de referencia de los benchmarks [6][7][8]; estimación de necesidades de elaboración propia.*

<svg viewBox="0 0 820 312" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">
  <rect x="0" y="0" width="820" height="312" rx="10" fill="#f7f9fb"/>
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
  <text x="410" y="293" text-anchor="middle" font-size="10.5" fill="#7c8a93">Con ~110 ops/seg/nodo (conservador) hacen falta 6 nodos; a ~120+ ops/seg/nodo bastan 5 → rango 5–6 (Tabla 3)</text>
</svg>

***Figura 3.** Capacidad acumulada al añadir nodos de repositorio Alfresco hasta superar el objetivo de 600 ops/seg. **Fuente:** rendimiento por nodo derivado de los benchmarks de Alfresco [6][7]; proyección lineal de elaboración propia.*

> **Conclusión de capacidad:** S3 sostiene 600 ops/seg **sin diseño adicional** (un solo prefijo, servicio gestionado). Alfresco sostiene 600 ops/seg pero **requiere dimensionar y operar 3 capas** (repositorio, índice, base de datos) con redundancia.

---

### 3.4 Amplificación de I/O

La métrica más reveladora a igual carga de **600 ops/seg lógicas** es cuánta **I/O física** se genera realmente en el backend.

| Plataforma | I/O por escritura | I/O por lectura | Amplificación agregada a 600 ops/seg (según mezcla L/E) |
|-----------|-------------------|-----------------|---------------------------------------------------------|
| **Amazon S3** | ≈ 1 | ≈ 1 | **≈ 1×** (dato) — ≈ 600 I/O de almacenamiento, gestionadas/transparentes |
| **Alfresco** *(estimado)* | ≈ 4–7 (BD + content store + Solr) | ≈ 2 (BD + content store) | **≈ 2× (todo lectura) a ≈ 5× (todo escritura)** · **~3×** en un perfil ECM con predominio de lectura — es decir, **≈ 1.200–3.000 I/O** repartidas en 3 subsistemas |

***Tabla 4.** Amplificación de I/O. El factor de Alfresco es una **estimación**, no una medición. **Fuente:** modelo de objetos de S3 [1]; arquitectura de tres capas de Alfresco [6][7][8][11]; elaboración propia.*

<svg viewBox="0 0 820 290" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">
  <rect x="0" y="0" width="820" height="290" rx="10" fill="#f7f9fb"/>
  <text x="410" y="28" text-anchor="middle" font-size="16" font-weight="700" fill="#1a2b34">I/O física por operación (Alfresco es estimación)</text>
  <rect x="470" y="42" width="12" height="12" fill="#d9743a"/><text x="487" y="52" font-size="10" fill="#555">BD</text>
  <rect x="525" y="42" width="12" height="12" fill="#4a6b8a"/><text x="542" y="52" font-size="10" fill="#555">Content store</text>
  <rect x="625" y="42" width="12" height="12" fill="#7a5aa8"/><text x="642" y="52" font-size="10" fill="#555">Solr</text>
  <line x1="200" y1="240" x2="760" y2="240" stroke="#cdd6dd" stroke-width="1.5"/>
  <text x="200" y="258" text-anchor="middle" font-size="9" fill="#7c8a93">0</text>
  <text x="280" y="258" text-anchor="middle" font-size="9" fill="#7c8a93">1</text>
  <text x="360" y="258" text-anchor="middle" font-size="9" fill="#7c8a93">2</text>
  <text x="440" y="258" text-anchor="middle" font-size="9" fill="#7c8a93">3</text>
  <text x="520" y="258" text-anchor="middle" font-size="9" fill="#7c8a93">4</text>
  <text x="600" y="258" text-anchor="middle" font-size="9" fill="#7c8a93">5</text>
  <text x="680" y="258" text-anchor="middle" font-size="9" fill="#7c8a93">6</text>
  <text x="760" y="258" text-anchor="middle" font-size="9" fill="#7c8a93">7  (I/O backend)</text>
  <text x="190" y="83" text-anchor="end" font-size="11.5" font-weight="700" fill="#9c5510">S3 · escritura</text>
  <rect x="200" y="68" width="80" height="24" rx="3" fill="#e07c1f"/>
  <text x="290" y="85" font-size="11" fill="#9c5510">≈ 1 (dato)</text>
  <text x="190" y="119" text-anchor="end" font-size="11.5" font-weight="700" fill="#9c5510">S3 · lectura</text>
  <rect x="200" y="104" width="80" height="24" rx="3" fill="#f0a050"/>
  <text x="290" y="121" font-size="11" fill="#9c5510">≈ 1 (dato)</text>
  <text x="190" y="163" text-anchor="end" font-size="11.5" font-weight="700" fill="#2c7a6b">Alfresco · escritura</text>
  <rect x="200" y="148" width="240" height="24" fill="#d9743a"/>
  <rect x="440" y="148" width="80" height="24" fill="#4a6b8a"/>
  <rect x="520" y="148" width="80" height="24" fill="#7a5aa8"/>
  <rect x="600" y="148" width="160" height="24" fill="none" stroke="#7a5aa8" stroke-dasharray="4 3"/>
  <text x="600" y="143" text-anchor="middle" font-size="9" fill="#7c8a93">rango hasta 7</text>
  <text x="528" y="190" text-anchor="middle" font-size="11" font-weight="700" fill="#2c7a6b">≈ 4–7 (est.)</text>
  <text x="190" y="219" text-anchor="end" font-size="11.5" font-weight="700" fill="#2c7a6b">Alfresco · lectura</text>
  <rect x="200" y="204" width="80" height="24" fill="#d9743a"/>
  <rect x="280" y="204" width="80" height="24" fill="#4a6b8a"/>
  <text x="370" y="221" font-size="11" font-weight="700" fill="#2c7a6b">≈ 2 (est.)</text>
  <text x="410" y="280" text-anchor="middle" font-size="11.5" font-weight="700" fill="#a8521f">Agregado a 600 ops/seg: ≈ 2× (todo lectura) a ≈ 5× (todo escritura) · ~3× en perfil ECM con predominio de lectura</text>
</svg>

***Figura 4.** I/O física por operación. Los factores de Alfresco son **estimación**, no medición. **Fuente:** modelo de objetos de S3 [1]; arquitectura de tres capas de Alfresco [6][7][8][11]; elaboración propia.*

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

| Plataforma | Latencia (con fuente) | Concurrencia para 600 ops/seg |
|-----------|------------------------|-------------------------------|
| S3 — p90 TTFB | ~20 ms [5] | 600 × 0,02 = **~12 conexiones** en vuelo |
| S3 — guía AWS | 100–200 ms [3] | 600 × 0,1–0,2 = **~60–120 conexiones** |
| Alfresco — operación típica | < 1 s [7] | 600 × 1,0 ≈ **~600 operaciones** en vuelo |
| Alfresco — operación compleja | < 4,5 s [6] | 600 × 4,5 ≈ **~2.700 operaciones** en vuelo |

***Tabla 5.** Concurrencia en vuelo necesaria para sostener 600 ops/seg según la Ley de Little. **Fuente:** latencias de S3 [3][5] y de Alfresco [6][7]; aplicación de la Ley de Little de elaboración propia.*

---

### 3.6 Tabla resumen comparativa (a 600 ops/seg)

| Dimensión | Amazon S3 | Alfresco Content Services |
|-----------|-----------|---------------------------|
| Capacidad nominal | ≥ 3.500 escr. / ≥ 5.500 lect. **por prefijo** [1] | ~100–140 ops/seg **por nodo** [6][7] |
| Recursos para 600 ops/seg | 1 prefijo (11–17 % de uso, cualquier mezcla) | 5–6 nodos repo + Solr + BD con IOPS |
| *Headroom* a 600 ops/seg | ≥ 5,8× (cualquier mezcla) | Ajustado; escala añadiendo nodos/*shards* |
| Amplificación de I/O | ≈ 1× (dato) | ≈ 4–7× escr. / ≈ 2× lect. — **≈ 2×–5× según mezcla (estimado)** |
| Latencia típica | ~20 ms p90 [5]; 100–200 ms guía [3] | < 1 s; hasta 4,5 s en operaciones complejas [6][7] |
| Concurrencia a 600 ops/seg | ~12–120 conexiones | ~600–2.700 operaciones en vuelo |
| Operación bajo carga | Auto-escalado; 503 *Slow Down* temporales [3] | Requiere *sharding* de Solr y tuning de BD [6] |
| Búsqueda full-text | No nativa | Nativa (Solr) |
| Metadatos / permisos finos / versionado | Limitado (tags, ACL de objeto) | Nativo y rico |
| Modelo operativo | Totalmente gestionado (serverless) | Autogestionado (3 capas con estado) |

***Tabla 6.** Resumen comparativo Alfresco vs. Amazon S3 a 600 ops/seg. **Fuente:** consolidación de las secciones 3.1–3.5.*

---

## 4. Recomendaciones

1. **Si el requisito es exclusivamente throughput de almacenamiento a 600 ops/seg → Amazon S3.** El objetivo cabe holgadamente en un único prefijo (**11–17 % de su capacidad bajo cualquier mezcla, ≥ 5,8× de margen**) [1][2], con amplificación de I/O ≈ 1 y sin necesidad de dimensionar ni operar infraestructura con estado.

2. **Si el requisito incluye capacidades ECM → Alfresco**, aceptando que sostener 600 ops/seg implica **5–6 nodos de repositorio + Solr + base de datos con IOPS provisionados** y una amplificación de I/O **estimada en ≈ 2×–5× según la mezcla lectura/escritura**.

3. **Arquitectura híbrida (recomendada en la mayoría de casos reales).** Usar **Alfresco como capa de gestión documental** y **S3 como *content store* subyacente**. La I/O pesada de objetos la absorbe S3 (amplificación ≈ 1 en esa capa) mientras Alfresco conserva las funciones de ECM.

4. **Dimensionar con margen y por capa.** Para Alfresco, a 600 ops/seg el límite suele aparecer en **base de datos** y **content store** por la amplificación de I/O. Aplicar ***sharding* de Solr** desde el diseño [6][8].

5. **Para S3, planificar el escalado gradual.** Ante picos súbitos pueden aparecer respuestas **503 *Slow Down***; implementar **reintentos con backoff exponencial** y evaluar **S3 Express One Zone** para latencias de un dígito de ms [3][4].

6. **Validar con un benchmark propio.** Las cifras por nodo de Alfresco (~100–140 ops/seg) provienen de benchmarks de 2007 y 2015 [6][7] y el factor de amplificación de I/O (≈2×–5×) es **estimado**, no medido. Antes de fijar el dimensionamiento definitivo, ejecutar una prueba de carga con la versión actual del producto y el perfil de operaciones real.

---

## Referencias

1. AWS — *Best practices design patterns: optimizing Amazon S3 performance*. https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance.html
2. AWS — *Amazon S3 Announces Increased Request Rate Performance*. https://aws.amazon.com/about-aws/whats-new/2018/07/amazon-s3-announces-increased-request-rate-performance/
3. AWS — *Performance design patterns for Amazon S3*. https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance-design-patterns.html
4. AWS — *New Amazon S3 Express One Zone high performance storage class*. https://aws.amazon.com/blogs/aws/new-amazon-s3-express-one-zone-high-performance-storage-class/
5. D. Vassallo — *s3-benchmark*. https://github.com/dvassallo/s3-benchmark
6. Alfresco / Amazon — *The Alfresco ECM 1 Billion Document Benchmark on AWS and Aurora*. https://www.slideshare.net/slideshow/the-alfresco-ecm-1-billion-document-benchmark-on-aws-and-aurora-benchmark-details-and-scalability-recommendations/54444004
7. Unisys / Alfresco — *Alfresco Benchmark Report (bl100093)*. https://www.slideshare.net/slideshow/alfresco-benchmark-reportbl100093/5869700
8. S. O'Kennedy — *Alfresco's Billion Documents – a Closer Look*. https://www.linkedin.com/pulse/alfrescos-billion-documents-closer-look-steven-o-kennedy
9. Crest Infosolutions / IBM — *Performance benchmarking of ACS on Red Hat OpenShift on IBM Power vs x86*. https://crestsolution.com/resources/whitepapers/performance-benchmarking-of-alfresco-content-services-acs-on-red-hat-openshift-on-ibm-power-vs-x86/
10. AWS re:Post — *Understanding reading rate limit from a single prefix in S3*. https://repost.aws/questions/QUM5pQi20uSWK3lWoCH34W5w/understanding-reading-rate-limit-from-a-single-prefix-in-s3
11. T. de la Fuente / Alfresco — *Sizing your Alfresco Platform*. https://www.slideshare.net/slideshow/sizing-your-alfrescoplatform/40139663
12. Alfresco / Hyland — *Set up clustering*. https://docs.alfresco.com/content-services/latest/admin/cluster/
13. Alfresco / Hyland — *What's new in Alfresco Content Services*. https://docs.alfresco.com/content-services/latest/release/
