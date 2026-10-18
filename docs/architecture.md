# Arquitectura

> Los componentes de 30X Signal y qué hace cada uno. El algoritmo de priorización está en
> [`scoring.md`](scoring.md) y el coste medido, en [`costs.md`](costs.md).

Un **monolito modular** en Python. Unos jobs recolectan señales públicas y las analizan; una sola
capa de servicios sirve el resultado al dashboard, al agente del Radar y a los asistentes de IA.
Ni el frontend ni el MCP calculan nada: leen lo que ya calculó el análisis.

![Componentes de 30X Signal: fuentes públicas, colectores, motor de análisis con modelos de IA, base de datos, servicios, API REST, agente Rad y servidor MCP, y los clientes](diagrams/arquitectura.svg)

## Componentes

| Componente | Qué hace |
|---|---|
| **Colectores** | Leen cada fuente pública de forma periódica y guardan las piezas con sus métricas |
| **Motor de análisis** | Agrupa las piezas en temas, calcula velocidad, outliers, etapa y scores, y guarda cada ejecución con su ranking |
| **Modelos de IA** | Jev (TypeSafe) clasifica cada pieza y verifica lo que se publica; el LLM evalúa el encaje con la audiencia y redacta |
| **Base de datos** | PostgreSQL: piezas, métricas, ejecuciones del análisis y briefs |
| **Servicios** | La única lógica de negocio. La comparten la API, el agente y el MCP, así que todos ven los mismos datos |
| **API REST** | Sirve oportunidades, evidencia, briefs y coste al dashboard |
| **Agente Rad** | Responde preguntas sobre el Radar y mueve la vista del dashboard |
| **Servidor MCP** | Las mismas consultas desde Claude, ChatGPT o Grok |
| **Dashboard** | Vue 3: Radar, exploración de la evidencia y creación de briefs |

## Principios

- **Python calcula; la IA evalúa y redacta.** Todos los scores son deterministas. Lo que escriben
  los modelos se comprueba contra la evidencia antes de publicarse.
- **Una ejecución fijada para la demo.** El ranking que se enseña es el de una ejecución revisada;
  el análisis puede seguir corriendo sin cambiarlo.
- **El texto de Internet es dato, nunca instrucción.** Llega a los modelos delimitado, y las piezas
  sospechosas se excluyen.
- **Solo datos públicos.** Metadatos, enlaces y métricas; nunca datos personales.

## Documentos relacionados

- [`scoring.md`](scoring.md): el algoritmo de priorización.
- [`costs.md`](costs.md): coste de operación medido.
- [`sources.md`](sources.md): fuentes y sus límites.
- [`jev.md`](jev.md): cómo usamos Jev.
- [`mcp.md`](mcp.md): tools MCP y cómo conectarse.
- [`brief.md`](brief.md): el reto y qué podemos afirmar con los datos.
