# Alumno: Jorge Ruiz
# Examen Python - Generador SQL de tickets
# Lee los tickets .txt de una carpeta, los valida y genera insert_ticket.sql con los INSERT
# de las 6 tablas de tickets_db. Cada ejecución se registra en tickets.log.
# Uso: python build_insert_from_tickets.py <carpeta_de_tickets>

import os
import sys
from datetime import datetime

ARCHIVO_SALIDA = "insert_ticket.sql"
ARCHIVO_LOG = "tickets.log"


# ---------------------------------------------------------------------------
# 0. MENSAJES Y LOG
# ---------------------------------------------------------------------------

def escribir_log(nivel, mensaje):
    """Añade una línea al log con fecha, hora y nivel (INFO o ERROR)."""
    momento = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Modo "a": añade al final sin borrar las ejecuciones anteriores
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as log:
        log.write(f"{momento} [{nivel}] {mensaje}\n")


def informar(mensaje):
    """Muestra un mensaje en la terminal y lo guarda en el log."""
    sys.stdout.write(mensaje + "\n")
    escribir_log("INFO", mensaje)


def avisar_error(mensaje):
    """Muestra un error por la salida de errores y lo guarda en el log."""
    sys.stderr.write(mensaje + "\n")
    escribir_log("ERROR", mensaje)


# ---------------------------------------------------------------------------
# 1. LEER UN TICKET
# ---------------------------------------------------------------------------

def es_linea_de_producto(linea):
    """True si la línea es un producto: empieza por espacios y luego un número."""
    texto = linea.strip()
    return linea.startswith(" ") and texto != "" and texto[0].isdigit()


def leer_producto(linea):
    """Convierte una línea de producto en un diccionario."""
    # "  2.500 Manzana Golden (kg)  3.12 €" -> cantidad, descripción, importe, "€"
    partes = linea.split()
    cantidad = float(partes[0])
    importe = float(partes[-2])
    if cantidad <= 0 or importe <= 0:
        raise ValueError(f"cantidad o importe incorrecto en '{linea.strip()}'")
    descripcion = " ".join(partes[1:-2])
    return {"cantidad": cantidad, "descripcion": descripcion, "importe": importe}


def leer_ticket(ruta):
    """Lee un ticket .txt y devuelve un diccionario con sus datos."""
    with open(ruta, "r", encoding="utf-8") as archivo:
        lineas = archivo.read().splitlines()

    # None = dato no encontrado todavía
    ticket = {
        "numero": None,
        "fecha_hora": None,
        "codigo_cajero": None,
        "nombre_cajero": None,
        "forma_pago": None,
        "autorizacion": None,  # los pagos en efectivo no tienen
        "subtotal": None,
        "iva": None,
        "total": None,
        "productos": [],
    }

    # Las 3 primeras líneas son siempre la sucursal
    ticket["sucursal_nombre"] = lineas[0].strip()
    ticket["sucursal_direccion"] = lineas[1].strip()
    partes = lineas[2].split()  # ["CIF:", "B12345678", "Tel:", "910123456"]
    ticket["cif"] = partes[1]
    ticket["telefono"] = partes[3]
    if len(ticket["cif"]) != 9:
        raise ValueError(f"CIF incorrecto: {ticket['cif']}")

    for linea in lineas:
        if linea.startswith("Fecha:"):
            partes = linea.split()  # ["Fecha:", "11/09/2025", "Hora:", "17:01"]
            # strptime lanza ValueError si la fecha no existe
            ticket["fecha_hora"] = datetime.strptime(partes[1] + " " + partes[3], "%d/%m/%Y %H:%M")

        elif linea.startswith("Cajero:"):
            codigo, nombre = linea.replace("Cajero:", "").split(" - ")
            codigo = codigo.strip()
            if not codigo.isdigit():
                raise ValueError(f"código de cajero incorrecto: {codigo}")
            ticket["codigo_cajero"] = int(codigo)
            ticket["nombre_cajero"] = nombre.strip()

        elif linea.startswith("Ticket:"):
            numero = linea.split()[1]
            if not numero.isdigit():
                raise ValueError(f"número de ticket incorrecto: {numero}")
            ticket["numero"] = int(numero)

        elif linea.startswith("SUBTOTAL"):
            ticket["subtotal"] = float(linea.split()[-2])
        elif linea.startswith("IVA"):
            ticket["iva"] = float(linea.split()[-2])
        elif linea.startswith("TOTAL"):
            ticket["total"] = float(linea.split()[-2])

        elif linea.startswith("FORMA DE PAGO:"):
            ticket["forma_pago"] = linea.split(":")[1].strip()
        elif linea.startswith("Autorización:"):
            ticket["autorizacion"] = linea.split(":")[1].strip()

        elif es_linea_de_producto(linea):
            ticket["productos"].append(leer_producto(linea))

    comprobar_ticket(ticket)
    return ticket


def comprobar_ticket(ticket):
    """Comprueba que el ticket está completo y que sus cuentas cuadran."""
    obligatorios = ["numero", "fecha_hora", "codigo_cajero", "forma_pago", "subtotal", "iva", "total"]
    for campo in obligatorios:
        if ticket[campo] is None:
            raise ValueError(f"falta el campo {campo}")

    if len(ticket["productos"]) == 0:
        raise ValueError("el ticket no tiene productos")

    suma_productos = 0.0
    for producto in ticket["productos"]:
        suma_productos += producto["importe"]

    # Se redondea a céntimos porque los float no son exactos
    if round(suma_productos, 2) != round(ticket["subtotal"], 2):
        raise ValueError("la suma de los productos no coincide con el subtotal")
    if round(ticket["subtotal"] + ticket["iva"], 2) != round(ticket["total"], 2):
        raise ValueError("subtotal + IVA no coincide con el total")


# ---------------------------------------------------------------------------
# 2. REPARTIR LOS DATOS EN LAS 6 TABLAS (sin repetir)
# ---------------------------------------------------------------------------

def crear_tablas_vacias():
    """Un diccionario por tabla; la clave es el dato que no se puede repetir."""
    return {
        "sucursal": {},    # CIF
        "empleado": {},    # código del cajero
        "forma_pago": {},  # nombre
        "producto": {},    # descripción
        "ticket": {},      # número de ticket
    }


def anadir_ticket(tablas, ticket):
    """Reparte los datos de un ticket entre las tablas, guardando cada cosa una sola vez."""
    if ticket["numero"] in tablas["ticket"]:
        raise ValueError(f"ticket repetido: {ticket['numero']}")

    # Los ids nuevos son len() + 1, así salen seguidos: 1, 2, 3...
    if ticket["cif"] not in tablas["sucursal"]:
        tablas["sucursal"][ticket["cif"]] = {
            "id": len(tablas["sucursal"]) + 1,
            "nombre": ticket["sucursal_nombre"],
            "direccion": ticket["sucursal_direccion"],
            "telefono": ticket["telefono"],
        }
    id_sucursal = tablas["sucursal"][ticket["cif"]]["id"]

    if ticket["codigo_cajero"] not in tablas["empleado"]:
        tablas["empleado"][ticket["codigo_cajero"]] = {
            "nombre": ticket["nombre_cajero"],
            "sucursal_id": id_sucursal,
        }

    if ticket["forma_pago"] not in tablas["forma_pago"]:
        tablas["forma_pago"][ticket["forma_pago"]] = len(tablas["forma_pago"]) + 1

    for producto in ticket["productos"]:
        if producto["descripcion"] not in tablas["producto"]:
            # Precio unitario = importe / cantidad, del primer ticket donde aparece
            tablas["producto"][producto["descripcion"]] = {
                "id": len(tablas["producto"]) + 1,
                "precio": round(producto["importe"] / producto["cantidad"], 2),
            }

    tablas["ticket"][ticket["numero"]] = ticket


# ---------------------------------------------------------------------------
# 3. ESCRIBIR EL ARCHIVO SQL
# ---------------------------------------------------------------------------

def texto_sql(valor):
    """Pone un texto entre comillas para SQL, duplicando las comillas internas (O'Brien -> 'O''Brien')."""
    return "'" + str(valor).replace("'", "''") + "'"


def generar_sql(tablas, nombre_archivo):
    """Escribe los DELETE e INSERT de todas las tablas en el archivo."""
    sentencias = ["USE tickets_db;"]

    # Se vacían las tablas para que solo queden los tickets válidos de esta ejecución.
    # Orden inverso a los INSERT por las claves foráneas.
    for tabla in ["ticket_linea", "ticket", "producto", "forma_pago", "empleado", "sucursal"]:
        sentencias.append(f"DELETE FROM {tabla};")

    # Primero las tablas de las que dependen las demás
    for cif, s in tablas["sucursal"].items():
        sentencias.append(
            f"INSERT INTO sucursal (id, nombre, direccion, cif, telefono) VALUES "
            f"({s['id']}, {texto_sql(s['nombre'])}, {texto_sql(s['direccion'])}, "
            f"{texto_sql(cif)}, {texto_sql(s['telefono'])});"
        )

    for codigo, e in tablas["empleado"].items():
        sentencias.append(
            f"INSERT INTO empleado (id, nombre, sucursal_id) VALUES "
            f"({codigo}, {texto_sql(e['nombre'])}, {e['sucursal_id']});"
        )

    for nombre, id_pago in tablas["forma_pago"].items():
        sentencias.append(f"INSERT INTO forma_pago (id, nombre) VALUES ({id_pago}, {texto_sql(nombre)});")

    for descripcion, p in tablas["producto"].items():
        sentencias.append(
            f"INSERT INTO producto (id, descripcion, precio) VALUES "
            f"({p['id']}, {texto_sql(descripcion)}, {p['precio']:.2f});"
        )

    for numero, t in tablas["ticket"].items():
        if t["autorizacion"] is None:
            autorizacion = "NULL"
        else:
            autorizacion = texto_sql(t["autorizacion"])
        fecha_hora = t["fecha_hora"].strftime("%Y-%m-%d %H:%M:%S")  # formato de MySQL
        id_pago = tablas["forma_pago"][t["forma_pago"]]

        sentencias.append(
            f"INSERT INTO ticket (numero, fecha_hora, empleado_id, subtotal, iva, total, forma_pago_id, autorizacion) "
            f"VALUES ({numero}, {texto_sql(fecha_hora)}, {t['codigo_cajero']}, {t['subtotal']:.2f}, "
            f"{t['iva']:.2f}, {t['total']:.2f}, {id_pago}, {autorizacion});"
        )

        for p in t["productos"]:
            id_producto = tablas["producto"][p["descripcion"]]["id"]
            sentencias.append(
                f"INSERT INTO ticket_linea (ticket_numero, producto_id, cantidad, importe) "
                f"VALUES ({numero}, {id_producto}, {p['cantidad']:.3f}, {p['importe']:.2f});"
            )

    with open(nombre_archivo, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(sentencias) + "\n")


# ---------------------------------------------------------------------------
# 4. PROGRAMA PRINCIPAL
# ---------------------------------------------------------------------------

def main():
    """Lee los tickets de la carpeta y genera insert_ticket.sql."""
    escribir_log("INFO", f"===== Inicio: {' '.join(sys.argv)} =====")

    if len(sys.argv) != 2:
        avisar_error("Uso: python build_insert_from_tickets.py <carpeta_de_tickets>")
        sys.exit(1)

    carpeta = sys.argv[1]
    if not os.path.isdir(carpeta):
        avisar_error(f"La carpeta '{carpeta}' no existe.")
        sys.exit(1)

    tablas = crear_tablas_vacias()

    # sorted() para que el orden (y el precio de cada producto) sea siempre el mismo
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.endswith(".txt"):
            continue

        # Un ticket con errores se descarta y se sigue con los demás
        try:
            ticket = leer_ticket(os.path.join(carpeta, nombre))
            anadir_ticket(tablas, ticket)
            escribir_log("INFO", f"{nombre}: correcto (ticket {ticket['numero']}, {len(ticket['productos'])} productos)")
        except (ValueError, IndexError) as error:
            avisar_error(f"{nombre}: descartado ({error})")

    generar_sql(tablas, ARCHIVO_SALIDA)

    informar(f"- Tickets: {len(tablas['ticket'])}")
    informar(f"- Empleados: {len(tablas['empleado'])}")
    informar(f"- Productos: {len(tablas['producto'])}")
    informar(f"- Formas de pago: {len(tablas['forma_pago'])}")
    informar(f"Generado {ARCHIVO_SALIDA}")


if __name__ == "__main__":
    main()
