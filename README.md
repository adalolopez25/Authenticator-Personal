# Authenticator — 2FA/TOTP de escritorio (offline)

App separada del Password Manager, con bóveda, master y repo propios.
Sustituye Google Authenticator en el PC con estándar abierto TOTP
(RFC 6238/4226, SHA-1/256/512, 6–8 dígitos, periodo configurable, `otpauth://`).

## Uso

```bat
pip install -r requirements.txt
python main.py                 :: dev (2 cuentas demo en DB temporal)
set PWM_PROD=1 & python main.py :: flujo real (crear/desbloquear bóveda)
pytest -q                       :: tests
```

## Advertencias honestas (leer antes de migrar)

1. **El reloj del PC debe estar sincronizado (NTP).** Deriva = códigos inválidos.
2. **TOTP no protege contra phishing.** Eso es terreno passkeys, fuera del MVP.
3. **Sin respaldo cifrado + códigos del proveedor, perder el PC = perder el 2FA.**
   Exporta la copia cifrada y guarda en papel los códigos de respaldo de cada sitio.
4. **Migración real por sitio:** Seguridad → 2FA → desactivar app actual →
   activar de nuevo → pegar secreto/URI aquí → verificar código →
   guardar códigos del proveedor en papel. El secreto no se puede extraer de la app vieja.

## Seguridad

Argon2id (t=3, 64 MiB, p=4) + AES-256-GCM, kit offline de un solo uso,
backoff tras 5 intentos, autobloqueo 3 min + al minimizar, clipboard auto-clear 15 s,
permisos 0600/0700, cero red. Detalle en `AGENTS.md`.
