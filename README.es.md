# Tool Evidence Guard

<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](LICENSE)

Verificador local de resultados de herramientas y afirmaciones estructuradas. Python >=3.10, sin dependencias de ejecución ni API de pago. Versión 0.1.0.

## Uso

Desde el directorio del repositorio clonado:

```sh
python3 -m tool_evidence_guard examples/valid.json
python3 -m tool_evidence_guard examples/unusable.json
python3 -m unittest discover -s tests -q
```

El primer ejemplo devuelve `OK`, el segundo `FAILED`. Son fixtures sintéticos de demostración, no resultados reales ni el dataset del paper.

Instalación aislada:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/tool-evidence-guard examples/valid.json
```

También acepta stdin (sin argumento o `-`). Códigos: 0 = conforme; 1 = rechazo; 2 = entrada ilegible, demasiado grande o JSON inválido. El informe no reproduce valores ni errores originales.

## Contrato de entrada

Documento JSON con `contract`, `result` y opcionalmente `claims`; otras claves raíz se rechazan.

- `contract.call_id`: identificador no vacío, asignado por el adaptador de confianza antes de ejecutar. `fields`: lista no vacía de reglas. `max_age_seconds`: opcional, positivo y finito.
- Cada regla contiene `path` (JSON Pointer bajo `/data/`) y `type` (`integer`, `number`, `string`, `boolean`). Opciones: `minimum`, `maximum` numéricos; `enum` de escalares del tipo declarado. Reglas desconocidas, duplicadas o mal escritas se rechazan. No es un validador JSON Schema completo.
- `result.status` debe ser exactamente `ok` y `call_id` debe coincidir. `data` contiene la salida capturada. La presencia de `error` rechaza incluso si es null: el adaptador debe omitirlo en éxito. Flags opcionales `truncated`, `stale`, `corrupted`, `redacted` deben ser booleanos: true rechaza. Otros metadatos se permiten, pero no son evidencia.
- `observed_at`: ISO 8601 con zona horaria. Es obligatorio cuando se exige frescura. Se rechazan fechas futuras. Debe proceder de la fuente/medición, no del momento de copiar un dato viejo.
- `claims`: lista de objetos exactamente `{ "path": ..., "value": ... }`. Solo igualdad escalar exacta y con el mismo tipo; no se interpretan prosa ni cálculos. Sin claims se verifican campos, pero `supported_claims` es 0.

Cada regla debe expresar lo que necesita la tarea ANTES de ver la respuesta. Para afirmar que una operación terminó, exigir un estado final y evidencia de lectura posterior, no solamente `status:ok` del envío.

## Comportamiento y límites

Detecta errores declarados, campos ausentes, tipos incorrectos, null, cadenas vacías, marcadores habituales de redacción, caracteres de sustitución, truncamiento declarado, datos antiguos, límites numéricos, enumeraciones y claims que contradicen los datos. Cero y false no se confunden con ausencia.

`retrieval_status: OK` significa conformidad con ESTE contrato; no certifica verdad, autoría, permisos, actualidad si no se exige, ni ejecución real. Un texto corrupto no reconocido puede pasar como string. Un proveedor puede mentir. El contrato y la captura son parte de la base de confianza: si el modelo fabrica ambos, este verificador no puede descubrirlo.

No analiza lenguaje natural, no es una defensa general contra prompt injection, no valida firmas, no elimina todas las alucinaciones y no intercepta automáticamente Hermes/Tars. No consulta red ni ejecuta las herramientas. La skill ofrece uso manual/asistido; un bloqueo obligatorio en el runtime queda pendiente.

CLI: máximo 1 MiB, JSON UTF-8 estricto sin claves duplicadas ni NaN/Infinity. API: máximo 10.000 nodos, profundidad 64 y presupuesto de caracteres. Solo estructuras JSON ordinarias; no objetos Python personalizados. El rechazo es global: si algo falla, cero claims aprobados.

## Arquitectura

- `tool_evidence_guard/__init__.py`: reglas, límites, resolución de rutas, frescura y claims.
- `tool_evidence_guard/cli.py`: lectura limitada y JSON estricto.
- `tool_evidence_guard/__main__.py`: entrada `python -m`.
- `tests/`: pruebas unitarias y CLI por subprocess.
- `examples/`: entradas sintéticas y demostración local.

## Fuente y evaluación

Inspirado en Sethi et al., “Fabrication After Tool Failure: Tool-Augmented Agents Assert Values Their Tools Did Not Return”, arXiv:2609.14758v1 (13-09-2026).
https://arxiv.org/abs/2609.14758

El paper estudia un indicador generado por el modelo y una intervención de prompt. Este proyecto aplica contratos deterministas: NO reproduce su experimento ni hereda sus porcentajes. Su apéndice A no ofrece aún enlace al repositorio; la búsqueda pública realizada no localizó una implementación oficial verificable. La publicación contiene límites y diferencias entre protocolos que impiden extrapolar una tasa universal.

## Licencia

[AGPL-3.0-or-later](LICENSE) — Copyright (C) 2026 Pedro Sordo Martínez <amurlaniakea@gmail.com>.
