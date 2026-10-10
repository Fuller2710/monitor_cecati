#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot de Monitoreo de Disponibilidad de Cursos - CECATI 95
URL: https://sites.google.com/view/cecati95inscripciones/inicio/cursos-s%C3%A1bados

Valida periódicamente el sitio web del CECATI 95 para detectar la apertura de inscripciones
y envía notificaciones automáticas por Telegram, Discord, Correo Electrónico (Email), WhatsApp o escritorio.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from html.parser import HTMLParser
import argparse
import subprocess

TARGET_URL = "https://sites.google.com/view/cecati95inscripciones/inicio/cursos-s%C3%A1bados"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "courses_state.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "monitor.log")

DEFAULT_CONFIG = {
    "url": TARGET_URL,
    "check_interval_seconds": 3600,
    "notify_on_every_check": False,
    "telegram": {
        "enabled": False,
        "bot_token": "TU_BOT_TOKEN_AQUI",
        "chat_id": "TU_CHAT_ID_AQUI"
    },
    "discord": {
        "enabled": False,
        "webhook_url": "TU_DISCORD_WEBHOOK_URL_AQUI"
    },
    "whatsapp_callmebot": {
        "enabled": False,
        "phone_number": "+521XXXXXXXXXX",
        "api_key": "TU_API_KEY_CALLMEBOT"
    },
    "email": {
        "enabled": False,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "tu_correo@gmail.com",
        "sender_password": "tu_app_password_de_gmail",
        "recipient_email": "destinatario@gmail.com"
    },
    "desktop_notification": {
        "enabled": True
    }
}


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        log(f"Archivo de configuración creado en '{CONFIG_FILE}'. Puedes editarlo con tus credenciales de notificación.")
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Mezclar con valores predeterminados para asegurar que todas las claves existan
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
                elif isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        if sub_k not in cfg[k]:
                            cfg[k][sub_k] = sub_v
            return cfg
    except Exception as e:
        log(f"Error al leer '{CONFIG_FILE}': {e}. Usando configuración por defecto.")
        return DEFAULT_CONFIG


class CECATICardParser(HTMLParser):
    """
    Parser HTML para extraer las tarjetas de cursos de Google Sites del CECATI 95.
    """
    def __init__(self):
        super().__init__()
        self.cards = []
        self.current_card = None
        self.in_card = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")
        if "tyJCtd" in cls:
            self.current_card = {"texts": [], "links": []}
            self.in_card = True
        if self.in_card and tag == "a" and "href" in attrs_dict:
            href = attrs_dict["href"]
            if href not in self.current_card["links"]:
                self.current_card["links"].append(href)

    def handle_endtag(self, tag):
        if tag == "div" and self.in_card:
            if self.current_card and self.current_card["texts"]:
                self.cards.append(self.current_card)
            self.current_card = None
            self.in_card = False

    def handle_data(self, data):
        if self.in_card:
            t = data.strip()
            if t:
                self.current_card["texts"].append(t)


def fetch_and_parse_courses(url: str) -> list:
    """
    Descarga el contenido de la página y extrae los cursos ofertados.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as response:
        raw_html = response.read().decode("utf-8", errors="replace")

    parser = CECATICardParser()
    parser.feed(raw_html)

    courses = []
    # Filtrar solo tarjetas que representen cursos
    for card in parser.cards:
        texts = card["texts"]
        # Una tarjeta de curso usualmente contiene: [Nombre Curso, Horario, Estado]
        # Ej: ['Instalaciones Eléctricas Residenciales Básicas', 'Sábados de 8 a 13', 'Cerrado']
        if len(texts) >= 2:
            # Descartar encabezados generales del sitio
            first_text = texts[0].lower()
            if any(term in first_text for term in ["cursos sábados", "si requieres ayuda", "google sites", "report abuse"]):
                continue

            # Identificar horario
            horario = ""
            estado = "Cerrado"
            nombre = texts[0]

            for t in texts[1:]:
                t_lower = t.lower()
                if "sábado" in t_lower or "sabado" in t_lower or "horario" in t_lower or "de 8 a" in t_lower or "de 13 a" in t_lower:
                    horario = t
                elif "cerrad" in t_lower:
                    estado = t
                elif any(word in t_lower for word in ["abiert", "disponib", "cupo", "inscr", "registro", "clic"]):
                    estado = t

            if len(texts) >= 3 and not estado:
                estado = texts[2]

            # Si no dice explícitamente "Cerrado", consideramos que podría estar abierto o disponible
            esta_disponible = "cerrad" not in estado.lower()

            courses.append({
                "nombre": nombre,
                "horario": horario if horario else (texts[1] if len(texts) > 1 else "No especificado"),
                "estado": estado,
                "disponible": esta_disponible,
                "enlaces": card["links"]
            })

    return courses


def load_previous_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Error al leer archivo de estado previo '{STATE_FILE}': {e}")
    return {}


def save_current_state(courses: list):
    state = {
        "last_checked": datetime.now().isoformat(),
        "courses": {f"{c['nombre']} ({c['horario']})": c for c in courses}
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
    except Exception as e:
        log(f"Error al guardar estado en '{STATE_FILE}': {e}")


def send_telegram_notification(cfg: dict, message: str) -> bool:
    t_cfg = cfg.get("telegram", {})
    if not t_cfg.get("enabled"):
        return False
    token = t_cfg.get("bot_token")
    chat_id = t_cfg.get("chat_id")
    if not token or not chat_id or "TU_BOT_TOKEN" in token:
        log("[Telegram] Configuración incompleta o token por defecto.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as res:
            if res.status == 200:
                log("[Telegram] Mensaje enviado exitosamente.")
                return True
    except Exception as e:
        log(f"[Telegram] Error al enviar mensaje: {e}")
    return False


def send_discord_notification(cfg: dict, message: str) -> bool:
    d_cfg = cfg.get("discord", {})
    if not d_cfg.get("enabled"):
        return False
    webhook_url = d_cfg.get("webhook_url")
    if not webhook_url or "TU_DISCORD" in webhook_url:
        log("[Discord] Webhook URL no configurado.")
        return False

    payload = {"content": message}
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            if res.status in [200, 204]:
                log("[Discord] Notificación enviada a Discord.")
                return True
    except Exception as e:
        log(f"[Discord] Error al enviar a Discord: {e}")
    return False


def send_whatsapp_callmebot(cfg: dict, message: str) -> bool:
    w_cfg = cfg.get("whatsapp_callmebot", {})
    if not w_cfg.get("enabled"):
        return False
    phone = w_cfg.get("phone_number")
    apikey = w_cfg.get("api_key")
    if not phone or not apikey or "TU_API_KEY" in apikey:
        log("[WhatsApp] Falta número o API Key de CallMeBot.")
        return False

    encoded_msg = urllib.parse.quote(message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_msg}&apikey={apikey}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as res:
            if res.status == 200:
                log("[WhatsApp] Mensaje enviado vía CallMeBot.")
                return True
    except Exception as e:
        log(f"[WhatsApp] Error al enviar WhatsApp: {e}")
    return False


def send_email_notification(cfg: dict, subject: str, message: str) -> bool:
    e_cfg = cfg.get("email", {})
    if not e_cfg.get("enabled"):
        return False
    smtp_server = e_cfg.get("smtp_server")
    smtp_port = e_cfg.get("smtp_port", 587)
    sender = e_cfg.get("sender_email")
    password = e_cfg.get("sender_password")
    recipient = e_cfg.get("recipient_email")

    if not sender or not password or not recipient or "tu_correo" in sender:
        log("[Email] Configuración de correo incompleta.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient

        part = MIMEText(message, "plain", "utf-8")
        msg.attach(part)

        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        log(f"[Email] Notificación enviada exitosamente a {recipient}.")
        return True
    except Exception as e:
        log(f"[Email] Error al enviar correo: {e}")
    return False


def send_desktop_notification(cfg: dict, title: str, message: str):
    desk_cfg = cfg.get("desktop_notification", {})
    if not desk_cfg.get("enabled", True):
        return

    # Windows Notification vía PowerShell Toast
    if sys.platform == "win32":
        try:
            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName("text")
            $textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode("{message[:200]}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("CECATI 95 Monitor")
            $notifier.Show($toast)
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, timeout=10)
        except Exception:
            pass


def dispatch_notifications(cfg: dict, title: str, message: str):
    """
    Distribuye el mensaje a todos los canales habilitados.
    """
    send_telegram_notification(cfg, message)
    send_discord_notification(cfg, message)
    send_whatsapp_callmebot(cfg, message)
    send_email_notification(cfg, title, message)
    send_desktop_notification(cfg, title, message)


def check_courses(cfg: dict, force_notify: bool = False) -> list:
    """
    Ejecuta una ronda de validación del sitio.
    Retorna la lista de cursos disponibles o recién abiertos.
    """
    url = cfg.get("url", TARGET_URL)
    log(f"Consultando página de cursos sábados en: {url} ...")

    try:
        current_courses = fetch_and_parse_courses(url)
    except Exception as e:
        log(f"Error al descargar o procesar la página: {e}")
        return []

    if not current_courses:
        log("No se pudieron extraer cursos de la página (la estructura podría haber cambiado).")
        return []

    log(f"Se encontraron {len(current_courses)} cursos en la oferta de Sábados.")
    prev_state = load_previous_state()
    prev_courses_map = prev_state.get("courses", {})

    available_courses = []
    newly_opened = []

    for c in current_courses:
        name = c["nombre"]
        course_key = f"{name} ({c['horario']})"
        prev = prev_courses_map.get(course_key) or prev_courses_map.get(name)
        status_str = f"[{c['estado']}]"
        log(f" - {name} ({c['horario']}): {status_str}")

        if c["disponible"]:
            available_courses.append(c)
            # Verificar si antes estaba cerrado o no existía
            if not prev or not prev.get("disponible", False):
                newly_opened.append(c)

    # Si estamos en GitHub Actions, escribir un resumen visual en GITHUB_STEP_SUMMARY
    github_summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if github_summary_file:
        try:
            with open(github_summary_file, "a", encoding="utf-8") as f:
                f.write("## 🎓 Reporte de Monitoreo - CECATI 95 (Sábados)\n\n")
                f.write(f"**Última revisión:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n")
                f.write(f"**URL:** [{url}]({url})\n\n")
                f.write("| Curso | Horario | Estado |\n")
                f.write("|---|---|---|\n")
                for item in current_courses:
                    icon = "🟢 **DISPONIBLE**" if item["disponible"] else "🔴 Cerrado"
                    f.write(f"| {item['nombre']} | {item['horario']} | {icon} |\n")
                f.write("\n")
        except Exception as e:
            log(f"Error escribiendo GITHUB_STEP_SUMMARY: {e}")

    # Si hay cursos recién abiertos
    if newly_opened:
        log(f"¡ALERTA! Se detectaron {len(newly_opened)} CURSOS ABIERTOS / DISPONIBLES!")
        lines = [
            "🚨 *¡CURSO(S) DISPONIBLE(S) EN CECATI 95!* 🚨\n",
            "Los siguientes cursos de sábados ya tienen inscripciones abiertas:\n"
        ]
        for item in newly_opened:
            links_str = f"\n   🔗 Liga: {item['enlaces'][0]}" if item["enlaces"] else ""
            lines.append(f"✅ *{item['nombre']}*\n   🕒 Horario: {item['horario']}\n   📌 Estado: {item['estado']}{links_str}\n")
        lines.append(f"\n🌐 *Visita el sitio:* {url}")

        msg = "\n".join(lines)
        dispatch_notifications(cfg, "¡Cursos Abiertos en CECATI 95!", msg)

        # Generar archivo markdown para crear un Issue en GitHub
        issue_file = os.path.join(BASE_DIR, "opened_courses.md")
        try:
            with open(issue_file, "w", encoding="utf-8") as f:
                f.write("## 🚨 ¡Se abrieron inscripciones en CECATI 95! 🚨\n\n")
                f.write("Los siguientes cursos han cambiado de estado o están disponibles para inscripción:\n\n")
                for item in newly_opened:
                    link_txt = f"\n  - **Enlace:** {item['enlaces'][0]}" if item["enlaces"] else ""
                    f.write(f"- ✅ **{item['nombre']}**\n  - **Horario:** {item['horario']}\n  - **Estado:** {item['estado']}{link_txt}\n\n")
                f.write(f"👉 **Visita la página oficial para inscribirte:** {url}\n")
        except Exception as e:
            log(f"Error al escribir '{issue_file}': {e}")

    elif available_courses and force_notify:
        lines = [
            "ℹ️ *Reporte de Cursos CECATI 95 (Sábados)*\n",
            "Cursos que actualmente aparecen como disponibles:\n"
        ]
        for item in available_courses:
            lines.append(f"• *{item['nombre']}* ({item['horario']}) - {item['estado']}")
        lines.append(f"\n🌐 {url}")
        msg = "\n".join(lines)
        dispatch_notifications(cfg, "Estado Cursos CECATI 95", msg)

    elif force_notify or cfg.get("notify_on_every_check", False):
        lines = [
            "ℹ️ *Reporte de Monitoreo CECATI 95 (Sábados)*\n",
            f"Hora de revisión: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            "Actualmente todos los cursos de sábados continúan con estado *CERRADO*.\n"
        ]
        for item in current_courses:
            lines.append(f"• {item['nombre']} ({item['horario']}): {item['estado']}")
        lines.append(f"\n🌐 {url}")
        msg = "\n".join(lines)
        dispatch_notifications(cfg, "Revisión CECATI 95: Sin cambios", msg)
    else:
        log("Todos los cursos permanecen cerrados. No se requieren notificaciones.")

    save_current_state(current_courses)
    return current_courses


def main():
    parser = argparse.ArgumentParser(description="Monitor de Disponibilidad de Cursos CECATI 95")
    parser.add_argument("--check-now", action="store_true", help="Ejecuta una sola verificación ahora y termina.")
    parser.add_argument("--notify-always", action="store_true", help="Envía notificación del estado actual aunque todo siga cerrado.")
    parser.add_argument("--test", action="store_true", help="Envía un mensaje de prueba a los canales de notificación configurados.")
    parser.add_argument("--daemon", action="store_true", help="Ejecuta el robot en bucle continuo según el intervalo de tiempo.")
    parser.add_argument("--interval", type=int, help="Intervalo en segundos entre cada chequeo en modo daemon.")
    args = parser.parse_args()

    cfg = load_config()

    if args.interval:
        cfg["check_interval_seconds"] = args.interval

    if args.test:
        test_msg = (
            "🔔 *Mensaje de Prueba - Bot CECATI 95*\n\n"
            "¡El sistema de notificaciones está funcionando correctamente!\n"
            f"Fecha y hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"URL monitoreada: {cfg.get('url', TARGET_URL)}"
        )
        log("Enviando mensaje de prueba a los canales habilitados...")
        dispatch_notifications(cfg, "Prueba Bot CECATI 95", test_msg)
        return

    if args.daemon:
        interval = cfg.get("check_interval_seconds", 3600)
        log(f"Iniciando modo demonio (revisión cada {interval} segundos / {interval/3600:.1f} horas)... Presiona Ctrl+C para detener.")
        try:
            while True:
                check_courses(cfg, force_notify=args.notify_always)
                log(f"Esperando {interval} segundos para el próximo chequeo...")
                time.sleep(interval)
        except KeyboardInterrupt:
            log("Monitoreo detenido por el usuario.")
    else:
        check_courses(cfg, force_notify=args.notify_always)


if __name__ == "__main__":
    main()
