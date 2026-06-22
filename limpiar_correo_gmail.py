import imaplib
import email
import time
from email.header import decode_header

# Datos de la cuenta
IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = "tu_correo@gmail.com"
PASSWORD = "tu_contraseña_app"

# Palabras clave en el asunto
PALABRAS_BLOQUEADAS = [
    "canva", "tiktok", "pelis", "promo", "PROMO",
    "ahorra", "descuento", "gratis", "oferta", "regalo",
    "compra ahora", "haz clic", "urgente", "última oportunidad",
    "dinero fácil", "gana dinero", "ganancias", "bitcoin",
    "seguros", "préstamo", "crédito", "banco",
    "viagra", "medicinas", "farmacia",
    "adulto", "xxx", "porn", "citas",
    "sorteo", "lotería", "ganador", "premio",
    "suscríbete", "newsletter", "curso", "seminario",
    "outlet", "rebajas", "liquidación", "clearance"
]

# Remitentes bloqueados
REMITENTES_BLOQUEADOS = [
    "newsletter@", "promo@", "no-reply@", "ventas@", "marketing@",
    "info@", "soporte@", "donotreply@", "noreply@"
]

def limpiar_texto(texto):
    """Decodifica cabeceras de correo (Subject, From, etc.)."""
    if not texto:
        return ""
    partes = decode_header(texto)
    resultado = ""
    for decoded, encoding in partes:
        if isinstance(decoded, bytes):
            try:
                resultado += decoded.decode(encoding if encoding else "utf-8", errors="ignore")
            except:
                resultado += decoded.decode("utf-8", errors="ignore")
        else:
            resultado += decoded
    return resultado

def conectar_imap():
    """Crea y devuelve una nueva conexión IMAP ya autenticada."""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, PASSWORD)
    mail.select("inbox")
    return mail

def revisar_y_borrar():
    mail = conectar_imap()

    # Buscar todos los correos
    status, mensajes = mail.search(None, "ALL")
    correos = mensajes[0].split()
    total = len(correos)
    print(f"Total de correos: {total}\n")

    bloque = 500
    eliminados_total = 0
    inicio_global = time.time()

    for i in range(0, total, bloque):
        lote = correos[i:i+bloque]
        inicio_bloque = time.time()
        eliminados_bloque = []

        print(f"\nProcesando correos {i+1} a {i+len(lote)} de {total}...\n")

        for num in lote:
            try:
                status, data = mail.fetch(num, "(RFC822)")
                if not data or not isinstance(data[0], tuple):
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = limpiar_texto(msg["Subject"] or "")
                from_ = limpiar_texto(msg.get("From") or "")

                # Verificar coincidencias
                if (any(p in subject.lower() for p in [w.lower() for w in PALABRAS_BLOQUEADAS]) or
                    any(r in from_.lower() for r in [r.lower() for r in REMITENTES_BLOQUEADOS])):

                    eliminados_bloque.append((num, from_, subject))
                    mail.store(num, "+FLAGS", "\\Deleted")

            except Exception as e:
                print(f"Error procesando correo {num}: {e}")
                continue  # ignora errores y sigue

        # Expunge para eliminar definitivamente
        try:
            mail.expunge()
        except imaplib.IMAP4.abort:
            print("Conexión perdida al expurgar. Reconectando...")
            mail = conectar_imap()
            mail.expunge()

        eliminados_total += len(eliminados_bloque)

        # Imprimir detalles del bloque
        if eliminados_bloque:
            for idx, (_, from_, subject) in enumerate(eliminados_bloque, start=1):
                print(f"{idx}. De: {from_} | Asunto: {subject}")

        duracion_bloque = time.time() - inicio_bloque
        bloques_restantes = (total - (i+len(lote))) // bloque
        tiempo_estimado = bloques_restantes * duracion_bloque

        print(f"\nBloque {i//bloque+1}: {len(eliminados_bloque)} correos eliminados "
              f"en {duracion_bloque:.2f} segundos.")
        print(f"⏳ Tiempo estimado restante: {tiempo_estimado/60:.1f} minutos.\n")

        # Reconectar cada 10 000 correos procesados
        if (i + bloque) % 10000 == 0:
            mail.close()
            mail.logout()
            print("Reconectando a Gmail para evitar corte de sesión...")
            mail = conectar_imap()

    duracion_total = time.time() - inicio_global
    print(f"Proceso completado en {duracion_total/60:.2f} minutos. "
          f"Total eliminados: {eliminados_total}")

    mail.close()
    mail.logout()

if __name__ == "__main__":
    revisar_y_borrar()
