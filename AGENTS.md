# AGENTS.md — Authenticator propio (PySide6 + Seguridad Máxima)

> Este archivo es OBLIGATORIO para cualquier agente (humano o IA) que trabaje en este repo.
> Prioridad: SEGURIDAD > FUNCIONALIDAD > ESTÉTICA. Si hay conflicto, gana seguridad.
> App SEPARADA del Password Manager: bóveda, master y repo propios. Nada compartido en caliente.

## 1. Proyecto — qué es / qué no es

* App desktop 2FA/TOTP independiente en **Python + PySide6 (Qt)**. Nada de Electron, nada web.
* Sustituye Google Authenticator en el PC (Google/GitHub/…) con estándar abierto
  TOTP (RFC 6238/4226, SHA-1/256/512, 6–8 dígitos, periodo configurable, `otpauth://`).
* **Prohibido incluir en código/docs/tests datos reales** (emails, secretos, URIs personales).
  Placeholders: `usuario@ejemplo.com`, `Mi Servicio`, secreto demo `JBSWY3DPEHPK3PXP`.
* Uso personal, offline-first. Sin telemetría, sin analytics, **cero red por defecto**.

## 2. Stack permitido (cerrado)

* UI: `PySide6` únicamente. Estilos vía `ui/styles/theme_dark.qss` + `ui/styles/animations.py`.
* Cripto: `cryptography` (AES-256-GCM), `argon2-cffi` (Argon2id). RNG: `secrets`. Nada de `random` para secretos.
* DB: `sqlite3` stdlib. Clipboard: `QClipboard` (auto-clear).
* Prohibido: `pycrypto`, `md5/sha1` para passwords, `pickle` para vault, `requests`, frameworks web, cámara en MVP.

## 3. Arquitectura obligatoria (espejo autocontenido del gestor)

```
main.py                 # PWM_PROD=1 real; dev con 2 cuentas demo
assets/icon.*           # variante candado+reloj (fuente icon.svg)
app/
  vault.py              # Argon2id + AES-GCM (copia del patrón, NADA compartido)
  auth.py               # master + kit de recuperación (mismo diseño)
  recovery.py           # kit offline Crockford + checksum (solo vía vault)
  store.py              # cuentas + papelera + reorder + export/import cifrado
  totp.py               # RFC 6238 stdlib (parse_any/parse_uri/generate)
  settings.py           # prefs NO secretas (autolock, clipboard, motion, last_backup)
  utils.py              # clipboard auto-clear
  version.py            # APP_VERSION única fuente
ui/
  main_window.py        # ventana COMPACTA vertical (auth 420x640, app 380x620)
  screens/accounts.py   # columna única: buscador + filas densas + añadir
  screens/add.py        # alta manual/URI + validación (código esperado)
  screens/prefs.py      # preferencias mínimas (diálogo, no sidebar)
  screens/welcome.py    # crear bóveda (master 12+ / 3 de 4 clases)
  screens/unlock.py     # desbloqueo + backoff 5 intentos
  screens/recovery.py   # kit: mostrar (una vez), usar, rotar
  widgets/icons.py      # 12 iconos SVG línea inline. Cero emojis.
  widgets/toasts.py     # slide + auto-dismiss 3s
  widgets/modal.py      # ModalHost: dim a mano + fade/slide
  styles/theme_dark.qss # ÚNICO archivo de colores
  styles/animations.py  # rise/stagger/shake + set_reduced()
installer/              # setup wizard + build.bat (mismo patrón)
tests/                  # test_totp.py (vectores RFC) + test_vault/store/auth
```

* Regla de imports: `ui/` NUNCA importa `cryptography`/`argon2` directo. Solo vía `app/vault.py` y `app/auth.py`.
* `store.py` NUNCA ve la master ni la key más tiempo del necesario. Semillas JAMÁS en claro en disco/logs/clipboard.
* Las semillas de los QR futuros se procesan en memoria y se descartan (fuera de MVP de todos modos).

## 4. Especificación criptográfica (NO negociable, heredada)

* KDF **Argon2id** `t=3, m=65536 (64 MiB), p=4, hash_len=32, salt_len=16` (salt `secrets.token_bytes`).
* **AES-256-GCM**, nonce 12 B por registro. Blob `v1.<base64(nonce|ciphertext|tag)>`. Fallo → genérico
  "datos corruptos o clave incorrecta" (sin oráculo).
* Verificador: `argon2.hash(master)` + `salt_kek` + `vault_check` (`"VAULT-OK"` cifrado). Login = verify + descifra check.
* Key en memoria: `bytearray` mutable, wipe `ctypes.memset` al bloquear. Autolock default **3 min** + al minimizar.
* Cambio de master: nuevo salt, re-cifra TODO, borra vieja. Atómico (transacción).
* Clipboard: solo el CÓDIGO (6–8 dígitos), auto-limpieza **15 s** + toast. La semilla JAMÁS va al clipboard.
* Intentos: 5 fallos → backoff (5s, 15s, 30s, 60s…). Mensaje genérico, no enumerar usuarios.
* Permisos `0o600` vault / `0o700` dir. Deps pineadas en `requirements.txt`.

### PROHIBICIONES

1. NUNCA plaintext (semillas/códigos/master) en disco, logs, prints, tracebacks, QSettings.
2. NUNCA `random`, `AES-ECB`, `Fernet` con password directa, XOR casero, base64 como "cifrado".
3. NUNCA hardcodear master, salt, nonce, key en código (la master dev es aleatoria por arranque).
4. NUNCA `repr`/`__str__` con secretos, ni secretos en screenshots/AGENTS.md/README.
5. NUNCA "recuperación por correo/teléfono": solo kit offline.
6. Export solo cifrado. Import tritura el origen. Sin export plaintext en MVP.

## 5. UI — ventana compacta vertical (restricción de diseño, §11 del plan)

* NADA de 3 columnas: **una sola columna**, ~380×620 (auth ~420×640), redimensionable pero pensada en pequeño.
* De arriba a abajo: topbar mínima (título + candado-lock + engranaje) → buscador → lista scrolleable → barra "+ Añadir".
* Fila densa: emisor + etiqueta (1 línea), código grande monoespaciado + barra fina de countdown, **clic en toda la fila = copiar**.
* Sin panel de detalle: todo pasa en la fila (renombrar/subir/bajar/eliminar en `⋮`; papelera con restaurar/purga).
* Auth/kit/alta/prefs = tarjetas/diálogos centrados compactos, mismo ancho. Sin sidebars ni side panels en MVP.
* Paleta (solo QSS): `bg #1E1E1E`, `sidebar #2A2138`, `card #2C2C2E`, `border #3A3A3C`,
  `label #B8A6E0`, `accent #6A58C4→hover #8A72E0`, `focus #1A7CFF`, `danger #FF6B6B`.
* Animaciones 150–300ms + `set_reduced()` en caliente (Preferencias + `REDUCED_MOTION=1`).

## 6. Flujo primer arranque vs desbloqueo

* Sin vault → `Welcome`: usuario local + master 2× (12+, 3 de 4 clases) → muestra KIT una sola vez → entrar.
* Con vault → `Unlock`: master, sin strength visible. Olvido = kit primero (re-cifra + kit fresco). Borrado total con clave actual como última salida.
* Post-login → lista en vivo (QTimer 1s) + alta + copiar. Papelera 30 días + purga. Reordenar persiste `position`.
* Dev (sin `PWM_PROD=1`): 2 cuentas demo genéricas en DB temporal. Real: `PWM_PROD=1`.

## 7. Calidad, tests y verificación

* Tests `pytest`: `test_totp.py` (vectores RFC 6238 apéndice B, 6 vectores × 3 algos + URI + base32 suelto),
  `test_vault.py` (roundtrip, tag-tamper, KDF, wipe), `test_store.py` (CRUD cifrado, papelera, reorder, backup),
  `test_auth.py` (crear/login, backoff, kit, change_master). Sin secretos en fixtures.
* Antes de commit: `python -m compileall .` + `pytest -q` verde. No commitear `data/`, `*.db`, `.venv/`.
* Barridos UI antes de entregar: stderr sin `QPainter`, `'\ufffd'` ausente, iconos 12/12 no-nulos, `data/` real intacta.
* Logs solo INFO sin PII. Reloj del PC sincronizado (NTP) o los códigos no valen — documentado en README.

## 8. Reglas de trabajo para agentes futuros

1. Leer este AGENTS.md completo antes de tocar código.
2. Mantener el plan letra por letra: MVP = alta secreto/URI, bóveda propia, lock/backoff/kit, lista viva, papelera, prefs mínimas, backup cifrado, instalador. v2 (QR/cámara, iconos por emisor, importar Google/Aegis/2FAS, portable, atajo global) FUERA.
3. Preferir editar sobre crear. No agregar deps sin justificar. No crear `.md` salvo pedido.
4. Placeholders siempre. Grep final de secretos antes de entregar.
5. Verificar con ejecución real (`pytest`, `python main.py` offscreen) y reportar hipótesis vs evidencia.
6. Idioma UI: español. Código: español o inglés consistente por archivo.
7. Migración real de cuentas = proceso manual por sitio (desactivar app vieja → activar de nuevo → capturar secreto → verificar → guardar códigos del proveedor en papel). No hay atajo ni extracción.

## 9. DONE MVP

* [ ] Alta por secreto y por URI, códigos correctos contra vectores RFC y 1 cuenta real.
* [ ] Bóveda cifrada en reposo, lock/backoff/kit verificados con tests.
* [ ] Export/import cifrado roundtrip + triturar origen; `pytest -q` verde; Setup instala/desinstala dejando `data/` intacta.

## 10. Historial de construcción — errores y soluciones (apuntar aquí, no repetir)

1. (2026-10-11) **Powershell `mkdir` con varias rutas falla** (ParameterBindingException).
   Solución: `New-Item -ItemType Directory -Force` por carpeta. Aplica a todo script `.bat`/docs de este repo.
2. (2026-10-11) **Decisión `secret_blob` como JSON empaquetado** (`pack_secret/unpack_secret`).
   Causa: dígitos/periodo/algo deben viajar cifrados con la semilla pero validarse al leer.
   Solución: JSON canónico `{"s","d","p","a"}` cifrado como un todo; `unpack` con error genérico. No separar columnas plaintext.
3. (2026-10-11, heredado del gestor) **Efectos QGraphicsOpacityEffect permanentes → warnings QPainter.**
   Solución: todo helper retira su efecto en `finished`; `stagger` solo hermanos; no-op si ya hay efecto.
4. (2026-10-11, heredado) **`bytearray(key)` copia la key (wipe no borra el original).**
   Estado: usar `bytearray` mutable extremo a extremo (`derive_key` ya lo devuelve); no convertir a `bytes` salvo en `AESGCM()` (solo lectura transitoria).
5. (Reservado) Anotar aquí cada bug real con causa → solución → verificación, antes del siguiente commit.
