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
  main_window.py        # shell escritorio 1280x800 (auth centrado 520x780). Sidebar + stack con fade.
  screens/accounts.py   # columna unica reutilizable (escritorio y futuro Android) + papelera (badge en sidebar)
  screens/add.py        # alta manual/URI + validación (código esperado)
  screens/prefs.py      # preferencias en 6 secciones con sub-nav (no sidebar lateral de app)
  screens/welcome.py    # crear bóveda (master 12+ / 3 de 4 clases)
  screens/unlock.py     # desbloqueo + backoff 5 intentos
  screens/recovery.py   # kit: mostrar (una vez), usar, rotar
  widgets/sidebar.py    # nav colapsable (Cuentas/Añadir/Papelera/Preferencias) + badge + versión
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

## 5. UI — escritorio amplio con sidebar (releva §11 del plan original a petición del usuario)

* Windows: ventana **1280×800** (mín 1024×680) con **sidebar colapsable** (`#2A2138`): Cuentas, Añadir cuenta,
  Papelera (badge con conteo), Preferencias + Bloquear + versión. Auth (welcome/unlock/kit) sigue centrado sin sidebar.
* Contenido: páginas con **fade al navegar**; sidebar con **`collapse_width`** (248↔68, 220ms).
* Android futuro: mismas pantallas en columna única sin sidebar (las pantallas no asumen el sidebar).

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
6. (2026-10-11) **`pyinstaller` no estaba en el PATH del shell** (CommandNotFoundException).
   Solución: usar `python -m PyInstaller` en `installer/build.bat` y en terminal. Verificación: build de
   `Authenticator.exe` (52 MB) + `Authenticator-Setup.exe` (99 MB) OK.
7. (2026-10-11) **Pillow no lee SVG** (los iconos fuente son `icon.svg`).
   Solución: renderizar con `QtSvg.QSvgRenderer` → `QImage` → `icon.png`, luego Pillow PNG→`icon.ico`
   (16–256px). Sin dependencias nuevas. Verificación: ambos exes con icono embebido, arranque 15 s sin crash.
8. (2026-10-11) **Faltaba bloqueo con Win+L/suspender y aviso Win+V** (gaps de auditoría).
   Solución: portado `ui/widgets/winframe.py` (WTSRegisterSessionNotification + dark titlebar + AppUserModelID)
   y `clipboard_history_on()` en `app/utils.py` con aviso en el toast de copia. Verificación: pytest verde + smoke offscreen.
9. (2026-10-11) **URL de GitHub API sin `repos/`** (`api.github.com/{owner}/{repo}/...` → 404).
   Causa: la ruta correcta es `api.github.com/repos/{owner}/{repo}/releases/latest`.
   La detectó el test en vivo contra la API real (el mock con monkeypatch no la cubría).
   Solución: `API_LATEST` corregida en `app/update.py`. Verificación: `fetch_latest()` real → 1.0.0 + setup_url válido;
   `is_newer(1.0.0, 1.0.0)=False`, `is_newer(1.0.0, 0.9.0)=True`.
10. (2026-10-11) **Release v1.0.0 quedó en draft por timeout** (150 MB de assets, subida lenta).
    Solución: `gh release upload` por asset + `gh release edit --draft=false`. Regla: publicar exige
    verificar `isDraft=false` y los 2 assets listados antes de darlo por hecho.
11. (2026-10-11) **Crash `libshiboken: C++ object already deleted` en `stagger`** (traceback real del usuario).
    Causa: `QTimer.singleShot` disparaba `rise_in` sobre filas ya borradas por un `reload` posterior.
    Solución: guard `_alive()` (prueba `objectName()` con `except RuntimeError`) en TODOS los helpers de
    `animations.py` + `try/except RuntimeError` en `_tick`/`refresh`. Verificación: stress 3×reload + ticks sin traceback.
12. (2026-10-11) **Lista blanca en modo Fusion** (viewport del QScrollArea sin estilo).
    Solución: base global `QWidget { background #1E1E1E }` + reglas `QScrollArea/viewport`, `QMenu`, `QToolTip`,
    `QAbstractItemView`. Verificación: muestreo de píxeles offscreen → viewport (30,30,30), cero blanco.
13. (2026-10-11) **Ventana 380×620 demasiado pequeña.**
    Solución: app 900×940 / auth 500×760 (mínimo 380×600) + columna de contenido max 640 centrada:
    en escritorio respira a los lados, en el futuro Android ocupa todo el ancho. Sin sidebars (restricción §11 intacta).
    NOTA POSTERIOR: el usuario pidió app grande con sidebar para Windows — ver §16 (releva §11 solo en escritorio).
14. (2026-10-11) **TypeError `TextInteractionFlag | int` al abrir Añadir/Kit.**
    Causa: flags crudos (`0x02 | 0x10`) mezclados con enums PySide6. Solución: `Qt.TextSelectableByMouse |
    Qt.TextSelectableByKeyboard` en `add.py`/`recovery.py`. Lo cazó el smoke de navegación (no había test que abriera esas pantallas).
15. (2026-10-11) **Crash al salir `-1073740791` en smoke con hilo de update vivo.**
    Causa: el QThread de chequeo competía con el teardown del intérprete. Solución: `stop()` del filtro
    nativo + `WTSUnRegister` + `_update_thread.wait(3000)` en `closeEvent`. Verificación: smoke con `w.close()` → `EXIT_CLEAN`, RC=0.
    OJO al testear animaciones offscreen: bombear el loop progresivamente (N×sleep+processEvents); un solo
    sleep+processEvents NO avanza QPropertyAnimation y finge que el colapso falla.
16. (2026-10-11) **Rediseño escritorio: sidebar + preferencias por secciones (§5/§11 actualizados).**
    Windows = ventana 1280×800 con sidebar colapsable (Cuentas/Añadir/Papelera+badge/Preferencias) y prefs en
    6 secciones (General/Seguridad/Clave/Recuperación y copias/Actualizaciones/Peligro). Android futuro = mismas
    pantallas en columna sin sidebar. Transiciones fade al navegar + `collapse_width` (QParallelAnimationGroup
    sobre min/maxWidth) para el sidebar.
17. (2026-10-11) **Segunda vuelta UI: prefs a modal + iconos + filas pro.**
    Preferencias = modal centrado bloqueante 880–960×620–700 con header+X (ya NO es página del stack: el sidebar
    restaura su selección al cerrar). Iconos 12→27 en `icons.py` (nav, filas, prefs, acciones). Filas con avatar
    2-letras + botón copiar + menú; header con refrescar + Añadir; estado vacío con CTA; footer de ayuda.
    Sidebar con botón chevron ARRIBA (ocultar/mostrar). Regla: `_move(up)=-1` (hacia índice 0); se invirtió una
    vez al reescribir y se corrigió antes del commit.
18. (2026-10-11) **Acabado moderno real (capturas del usuario): gradientes + tarjetas + subcontroles.**
    `QPushButton#primary` y `sideBtn:checked` con `qlineargradient` violeta; `#row` con contraste real
    (#2E2E32/borde #45454A, verificado por píxel) + hover elevado; filas con segundos restantes (`#remain`,
    rojo en urgente); Añadir = header con icono + tarjeta + `previewCard` con código gigante + botones lado a lado;
    auth envuelto en tarjeta con icono (lock/kit); `QSpinBox::up/down-button` y `QComboBox::drop-down` compactos
    (eran flechas gigantes sin estilo); `QScrollBar:horizontal { height: 0 }` + `AlwaysOff` en el nav (barra fantasma).
    OJO: métricas de scrollbar offscreen (100/30) son artefacto del plugin offscreen — en real se ven finas y no hay
    warnings de parse del QSS; la verificación válida es captura real + pixel-check de colores.
19. (2026-10-11) **REPLANTEO UI — sistema de diseño obligatorio (queja "todo simple").**
    Reglas que ya no se rompen:
    a) CERO texto de proceso/documentación en vistas: solo microcopy de acción (qué hacer / qué pasa).
       Detalle técnico → `QToolTip` de su control. Internos (KDF, backoff, MVP, NTP) → README/AGENTS, jamás la vista.
       Excepciones: avisos críticos irreversibles (kit una-vez, borrado) en `InfoBox` warn/danger.
    b) Avisos SIEMPRE en `ui/widgets/info.py:InfoBox` (tono info/warn/danger/ok), nunca `QLabel#muted` suelto.
    c) `QCheckBox` estilizado por QSS (`::indicator` 18px + checked violeta); prohibido el cuadro Fusion.
    d) Botones con icono + texto claro + tooltip con el detalle ("los botones muestran la información").
    e) Bordes limpios: cards `#2E2E32` + borde 1px `#45454A` + radio 12–16; hover = borde `#7A63D6` (sin dobles bordes).
    f) Cero vacío accidental: listas en **grid responsive** (`_cols_for_width` sobre `self.width()`, NO el viewport
       — el viewport miente antes del layout) 2↔1 columnas; estados vacíos con CTA; footer solo con acción real
       (Vaciar papelera). Contadores cortos ("2 cuentas", sin "protegidas con...").
    g) Secciones con `_section(icono, titulo)` + stat tiles con número grande; sub-nav sin h-scroll.
    h) Verificación UI: stagger/tick tolerantes + pixel-check de tarjeta + cols 2↔1 + salida limpia RC=0.
20. (2026-10-11) **Vista Cuentas paso 1: mosaicos + modal de código único.**
    Decisión del usuario: NINGÚN código en la lista (con 20+ cuentas no se entiende nada).
    Mosaicos grandes (`AccountTile` 200×150 mín): monograma 2-letras 76px con color determinista por emisor
    (`ui/widgets/issuer.py`: sha256→12 colores FIJOS en QSS `#tileMono[c]`, nada de `random`), emisor + etiqueta.
    Clic = `AccountModal` (400–460px) con el ÚNICO código en vivo (QTimer propio, 44px mono), barra + segundos,
    Copiar primario y acciones (Renombrar/Subir/Bajar/Eliminar o Restaurar/Eliminar-definitivo en papelera).
    Grid `width//240` (1–4 cols) con stretch igual: siempre llena el lado derecho, cero hueco.
    Sin logos de marcas (assets): offline + marcas + calidad del trazo a mano → monogramas como Google Authenticator.
    El modal cierra solo si se bloquea/elimina; cada tick renueva `_last_active` (mirar ≠ inactivo).
21. (2026-10-11) **Mosaicos grandes 2-col + iconos de plataforma + BUG `WA_StyledBackground`.**
    Grid max 2 columnas (`width>=600`), mosaicos 220×170 mín con stretch igual: 2 ocupan todo el ancho,
    el resto debajo. `brands.py`: 9 glifos verificados visualmente (contact sheet) estilo Feather/línea —
    github, google G, microsoft, facebook, instagram, X, twitch, linkedin, telegram — con `match_brand()` por
    palabras clave; resto = monograma. `issuer.art_label()` centraliza icono-vs-monograma (lista + modal).
    BUG GRAVE cazado: el fondo QSS del mosaico NO se pintaba en ventana (sí en grab propio) porque los QWidget
    custom necesitan `setAttribute(Qt.WA_StyledBackground, True)` — el mismo bug latente que tenían las filas
    `#row` (el pixel-check en esquina redondeada lo ocultó). REGLA: todo widget custom con fondo/borde QSS lo lleva;
    verificación = sample en composición de ventana, JAMÁS grab propio. Tests Qt siempre en subproceso
    (el teardown Qt en pytest rompe el proceso con -1073740791).
22. (2026-10-11) **Modal de cuenta pro (600px): chips + borde tintado + feedback + Ctrl+C.**
    Tarjeta 520–600, código 56px mono seleccionable, arte 76px, chips (`6 dígitos · 30 s · SHA1`),
    borde de la tarjeta tintado con el color del emisor (`#previewCard[c]`), Copiar con estado "¡Copiado!" 1.2s,
    atajo Ctrl+C, X con tooltip Esc. OJO: en un grab offscreen apareció un destello naranja transitorio en la
    esquina del arte; el censo de píxeles del modal (12 colores top) NO contiene naranja — artefacto de frame
    (deleteLater/repolish a medio pintar), no bug. Si reaparece en captura REAL, reabrir.
23. (2026-10-11) **Sidebar final: sin Añadir, prefs abajo, colapso fluido, vacío centrado.**
    El sidebar solo navega (Cuentas/Papelera); Añadir vive SOLO en el header (modal `open_add_modal`,
    Cancelar + Guardar, cierra solo al guardar). Preferencias encima de Bloquear (zona inferior).
    Colapso fluido real: `collapse_width` 240ms + swap de textos a MITAD (`QTimer.singleShot(120)`) —
    verificado con anchos intermedios (72…101…199…252), no salto seco.
    EmptyState centrado vertical de verdad (stretch 1 arriba/abajo del mensaje en el grid).
