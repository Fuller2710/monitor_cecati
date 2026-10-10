# 🤖 Monitor Automático de Cursos CECATI 95 (Sábados)

Script automatizado en Python para monitorear la página oficial de inscripciones del **CECATI 95** ([Cursos Sábados](https://sites.google.com/view/cecati95inscripciones/inicio/cursos-s%C3%A1bados)) y avisarte de forma inmediata tan pronto como se abra el cupo o la inscripción de cualquier curso.

---

## 🚀 Características

- **Sin dependencias externas**: Utiliza únicamente la librería estándar de Python (`urllib`, `html.parser`, `json`).
- **Detección inteligente**:
  - Extrae nombre, horario y estado actual de cada curso.
  - Guarda el historial en `courses_state.json` para saber si un curso cambió de *Cerrado* a *Abierto/Disponible*.
  - Detecta si se añade un nuevo curso o un enlace de formulario de inscripción.
- **Canales de Notificación**:
  - 🐙 **100% Nativo en GitHub**: Te crea un **Issue** automáticamente asignado a ti, enviándote un **correo directo a tu email de GitHub** y notificación a la app móvil de GitHub (¡sin configurar bots ni plataformas externas!).
  - 📊 **Dashboard visual en GitHub Actions**: Resumen con tabla de estados en cada ejecución.
  - 📱 **Telegram** (Opcional).
  - 💬 **Discord** (Opcional).
  - 🟢 **WhatsApp** (Opcional).
  - 📧 **Correo Electrónico SMTP** (Opcional).
  - 🖥️ **Notificación de escritorio Windows** (Toast).
- **Modos de Ejecución**:
  - Ejecución única manual o programada (`--check-now`).
  - Modo demonio en segundo plano (`--daemon --interval 3600`).
  - Nube 24/7 gratuita mediante **GitHub Actions**.
  - Tarea programada en **Windows Task Scheduler**.

---

## 📋 Cursos de Sábados Monitoreados

El robot analiza las 13 materias ofertadas para sábados:
1. *Instalaciones Eléctricas Residenciales Básicas* (8 a 13)
2. *Mantenimiento Preventivo a Motores Eléctricos* (13 a 18)
3. *Reparación de Refrigeradores* (8 a 13)
4. *Mantenimiento de Equipos de Aire Acondicionado Tipo Minisplit* (13 a 18)
5. *Mantenimiento Preventivo de Vehículos* (8 a 13)
6. *Conocimientos Básicos de Costura* (8 a 13)
7. *Pantalón para Caballero* (13 a 17)
8. *Inglés Básico I* (8 a 13)
9. *Inglés Básico I* (13 a 18)
10. *Inglés Preintermedio I* (8 a 13)
11. *Herramientas Digitales Básicas* (8 a 13)
12. *Excel Básico* (13 a 18)
13. *Contabilidad Básica* (8 a 13)

---

## ⚙️ Configuración Rápida

Edita el archivo [`config.json`](config.json):

### 1. Configurar Alertas por Telegram (Opción recomendada)

1. Abre Telegram y busca al usuario `@BotFather`.
2. Envía el comando `/newbot`, dale un nombre y copia el **Token** generado (ej. `123456789:ABCdefGhIJKlmNoPQRstuVWXyz`).
3. Busca al usuario `@userinfobot` en Telegram y envíale cualquier mensaje para obtener tu **Id numérico** (Chat ID).
4. En `config.json` coloca:
   ```json
   "telegram": {
       "enabled": true,
       "bot_token": "TU_BOT_TOKEN",
       "chat_id": "TU_CHAT_ID"
   }
   ```
5. Prueba que funcione ejecutando:
   ```bash
   python monitor_cecati.py --test
   ```

---

## 🛠️ Modos de Uso

### 1. Revisión manual o única
```bash
python monitor_cecati.py --check-now
```

### 2. Modo continuo (cada 1 hora = 3600 segundos)
```bash
python monitor_cecati.py --daemon --interval 3600
```

### 3. Forzar notificación con el estado actual (para probar)
```bash
python monitor_cecati.py --notify-always
```

---

## ⏰ Automatización Diaria

### Opción A: En tu computadora con Windows (Programador de Tareas)
Ejecuta el script PowerShell incluido para que se revise diariamente a las 9:00 AM:
```powershell
powershell -ExecutionPolicy Bypass -File .\setup_windows_task.ps1
```
O simplemente dale doble clic al archivo `run_daily.bat`.

---

### Opción B: En la Nube 24/7 Gratis con GitHub Actions (Sin encender tu PC)
1. Sube este proyecto a tu repositorio de GitHub (público o privado).
2. Ve a **Settings > Secrets and variables > Actions** en tu repositorio de GitHub.
3. Agrega tus secretos:
   - `TELEGRAM_BOT_TOKEN`: Token de tu bot.
   - `TELEGRAM_CHAT_ID`: Tu ID de chat en Telegram.
4. El flujo `.github/workflows/monitor.yml` se ejecutará automáticamente todos los días a las 8:00 AM y 2:00 PM (hora de México) y te enviará un mensaje si se abre un curso.
