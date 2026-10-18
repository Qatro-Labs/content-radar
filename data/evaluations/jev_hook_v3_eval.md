# Validación del gancho de Jev (`piece.v3`, preguntas `hook` y `hook_rev`)

18/10/2026 · modelo `jev-1.13.0`.

**Resultado: se usa.** Supera el umbral de `docs/jev.md` (≥ 70 % de acuerdo para usar una pregunta
en la demo).

## Muestra

Las 40 piezas con respuestas guardadas de la batería v3 (`jev_piece_v3_answers.json`). Un evaluador
LLM a ciegas (Claude) etiquetó el gancho de cada título sin ver las respuestas de Jev, con las mismas
opciones de la batería, más `unclear` si ninguna encaja. Las etiquetas se commitearon antes de
compararlas (`jev_hook_v3_labels.csv`, commit «Add blind hook labels…»).

## Resultados

La decisión es la de producción (`intelligence/jev.py`, `_choice`): `hook` y `hook_rev` coinciden y
la probabilidad máxima es ≥ 0,6; si no, el gancho queda incierto.

| Medida | Resultado |
| --- | --- |
| Piezas con etiqueta clara | 36 de 40 (4 `unclear`) |
| Jev decide | 31 de 36 (86 %) |
| **Acuerdo cuando Jev decide** | **29 de 31 (94 %)** |
| Acuerdo de `hook` solo, sin `hook_rev` | 33 de 36 (92 %) |

- **Los dos desacuerdos:** una historia que Jev lee como pregunta y una noticia de producto que lee
  como «cómo hacer».
- **Las 5 inciertas:** en 2 piezas `hook` y `hook_rev` dan opciones distintas. En las otras 3
  coinciden pero con probabilidad < 0,6, y en 2 de ellas aciertan la etiqueta.

**Limitaciones:** la muestra es pequeña, y 20 de las 36 etiquetas son `news`, así que el acuerdo en
los ganchos menos frecuentes se apoya en pocas piezas. La muestra no es la de los outliers.
