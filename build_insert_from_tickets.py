# Alumno: Jorge Ruiz
# Examen Python - Generador SQL de tickets
# Lee todos los tickets .txt de la carpeta que se le pasa como argumento, comprueba que cada uno
# es correcto, genera el archivo insert_ticket.sql con los INSERT de las 6 tablas de tickets_db
# y lo carga en MySQL, para que la base de datos quede igual que los tickets válidos de la carpeta.
# Todo lo que pasa en cada ejecución se guarda, con fecha y hora, en tickets.log.
# Uso: python build_insert_from_tickets.py <carpeta_de_tickets>
# (la primera vez hay que crear la base de datos con schema.sql)

import os                      # para listar los archivos de la carpeta y comprobar que existe
import sys                     # sys.argv (argumentos), sys.stdout/sys.stderr (escribir) y sys.exit (salir)
from datetime import datetime  # para convertir "11/09/2025 17:01" en una fecha de verdad y validarla
import mysql.connector         # el conector: la librería que permite a Python hablar con MySQL

ARCHIVO_SALIDA = "insert_ticket.sql"

# Datos de conexión de XAMPP por defecto: usuario root sin contraseña.
# Ojo: en un servidor de verdad root SIEMPRE tiene contraseña y no se usa para las aplicaciones.
DATOS_CONEXION = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "tickets_db",
}

# Archivo donde se guarda el historial de todas las ejecuciones
ARCHIVO_LOG = "tickets.log"


# ---------------------------------------------------------------------------
# 0. MENSAJES Y LOG
# ---------------------------------------------------------------------------

def escribir_log(nivel, mensaje):
    """Añade una línea al archivo .log con la fecha y hora, el nivel (INFO o ERROR) y el mensaje."""
    # datetime.now() es el momento actual; strftime lo convierte en texto con el formato que queremos
    momento = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Modo "a" (append = añadir): escribe al final del archivo sin borrar lo que ya había,
    # así el log guarda el historial de todas las ejecuciones. Si el archivo no existe, lo crea.
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as log:
        log.write(f"{momento} [{nivel}] {mensaje}\n")


def informar(mensaje):
    """Muestra un mensaje normal en la terminal y lo guarda en el log."""
    sys.stdout.write(mensaje + "\n")  # write() no añade el salto de línea, por eso el "\n"
    escribir_log("INFO", mensaje)


def avisar_error(mensaje):
    """Muestra un error en la salida de errores (sys.stderr) y lo guarda en el log."""
    sys.stderr.write(mensaje + "\n")
    escribir_log("ERROR", mensaje)


# ---------------------------------------------------------------------------
# 1. LEER UN TICKET
# ---------------------------------------------------------------------------

def es_linea_de_producto(linea):
    """Devuelve True si la línea es un producto, por ejemplo '  2   Arroz Redondo 1kg   2.30 €'."""
    texto = linea.strip()
    # Un producto empieza con espacios y lo primero que se ve es un número (la cantidad)
    return linea.startswith(" ") and texto != "" and texto[0].isdigit()


def leer_producto(linea):
    """Convierte una línea de producto en un diccionario. Lanza ValueError si los números no son válidos."""
    # "  2.500 Manzana Golden (kg)    3.12 €" -> ["2.500", "Manzana", "Golden", "(kg)", "3.12", "€"]
    partes = linea.split()
    cantidad = float(partes[0])  # float porque los productos al peso llevan decimales
    importe = float(partes[-2])  # el penúltimo trozo (el último es "€")
    if cantidad <= 0 or importe <= 0:
        # raise "lanza" un error a propósito. Lo recogerá el try/except de main()
        raise ValueError(f"cantidad o importe incorrecto en '{linea.strip()}'")
    descripcion = " ".join(partes[1:-2])  # lo del medio, vuelto a unir con espacios
    return {"cantidad": cantidad, "descripcion": descripcion, "importe": importe}


def leer_ticket(ruta):
    """Lee un ticket .txt y devuelve un diccionario con todos sus datos."""
    with open(ruta, "r", encoding="utf-8") as archivo:
        # splitlines() parte el texto en una lista de líneas. La necesitamos como lista (y no
        # recorrer el archivo directamente) para poder ir a las 3 primeras líneas por su posición.
        lineas = archivo.read().splitlines()

    # Los campos obligatorios empiezan en None ("sin valor"). Si al terminar alguno sigue en None,
    # es que esa línea no estaba en el ticket y lo damos por incorrecto.
    ticket = {
        "numero": None,
        "fecha_hora": None,
        "codigo_cajero": None,
        "nombre_cajero": None,
        "forma_pago": None,
        "autorizacion": None,  # este puede quedarse en None: los pagos en efectivo no tienen
        "subtotal": None,
        "iva": None,
        "total": None,
        "productos": [],
    }

    # --- Cabecera: las 3 primeras líneas son siempre los datos de la sucursal ---
    ticket["sucursal_nombre"] = lineas[0].strip()
    ticket["sucursal_direccion"] = lineas[1].strip()
    # "CIF: B12345678  Tel: 910123456" -> ["CIF:", "B12345678", "Tel:", "910123456"]
    partes = lineas[2].split()
    ticket["cif"] = partes[1]
    ticket["telefono"] = partes[3]
    if len(ticket["cif"]) != 9:  # un CIF español tiene siempre 9 caracteres
        raise ValueError(f"CIF incorrecto: {ticket['cif']}")

    # --- Resto del ticket: miramos cómo empieza cada línea para saber qué dato lleva ---
    for linea in lineas:
        if linea.startswith("Fecha:"):
            # "Fecha: 11/09/2025        Hora: 17:01" -> ["Fecha:", "11/09/2025", "Hora:", "17:01"]
            partes = linea.split()
            # strptime convierte el texto en fecha siguiendo el patrón (%d día, %m mes, %Y año,
            # %H hora, %M minutos). Si la fecha no existe (por ejemplo 31/02) lanza ValueError solo.
            ticket["fecha_hora"] = datetime.strptime(partes[1] + " " + partes[3], "%d/%m/%Y %H:%M")

        elif linea.startswith("Cajero:"):
            # "Cajero: 015 - Juan Pérez" -> quitamos "Cajero:" y partimos por " - "
            codigo, nombre = linea.replace("Cajero:", "").split(" - ")
            codigo = codigo.strip()
            if not codigo.isdigit():  # isdigit() es True si el texto son solo cifras
                raise ValueError(f"código de cajero incorrecto: {codigo}")
            ticket["codigo_cajero"] = int(codigo)  # int("015") = 15
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
        elif linea.startswith("TOTAL"):  # no confunde con SUBTOTAL: esa línea empieza por "SUB"
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
    """Comprueba que el ticket está completo y que sus cuentas cuadran. Si no, lanza ValueError."""
    obligatorios = ["numero", "fecha_hora", "codigo_cajero", "forma_pago", "subtotal", "iva", "total"]
    for campo in obligatorios:
        if ticket[campo] is None:
            raise ValueError(f"falta el campo {campo}")

    if len(ticket["productos"]) == 0:
        raise ValueError("el ticket no tiene productos")

    suma_productos = 0.0
    for producto in ticket["productos"]:
        suma_productos += producto["importe"]

    # round(..., 2) porque los float no son exactos (0.1 + 0.2 = 0.30000000000000004).
    # Redondeando a céntimos comparamos lo que de verdad importa.
    if round(suma_productos, 2) != round(ticket["subtotal"], 2):
        raise ValueError("la suma de los productos no coincide con el subtotal")
    if round(ticket["subtotal"] + ticket["iva"], 2) != round(ticket["total"], 2):
        raise ValueError("subtotal + IVA no coincide con el total")


# ---------------------------------------------------------------------------
# 2. REPARTIR LOS DATOS EN LAS 6 TABLAS (sin repetir)
# ---------------------------------------------------------------------------

def crear_tablas_vacias():
    """Devuelve un diccionario por tabla. La clave de cada uno es el dato que no se puede repetir."""
    return {
        "sucursal": {},    # clave: CIF                -> {id, nombre, direccion, telefono}
        "empleado": {},    # clave: código del cajero  -> {nombre, sucursal_id}
        "forma_pago": {},  # clave: nombre (TARJETA)   -> id
        "producto": {},    # clave: descripción        -> {id, precio}
        "ticket": {},      # clave: número de ticket   -> el ticket entero
    }


def anadir_ticket(tablas, ticket):
    """Reparte los datos de un ticket entre las tablas, guardando cada cosa una sola vez."""
    # Un número de ticket repetido es un error: en la base de datos es la clave primaria
    if ticket["numero"] in tablas["ticket"]:
        raise ValueError(f"ticket repetido: {ticket['numero']}")

    # Sucursal: solo se añade si su CIF no estaba ya. El id es el siguiente número libre
    # (si hay 0 sucursales, len() + 1 = 1; si hay 1, será 2...), así los ids van seguidos.
    if ticket["cif"] not in tablas["sucursal"]:
        tablas["sucursal"][ticket["cif"]] = {
            "id": len(tablas["sucursal"]) + 1,
            "nombre": ticket["sucursal_nombre"],
            "direccion": ticket["sucursal_direccion"],
            "telefono": ticket["telefono"],
        }
    id_sucursal = tablas["sucursal"][ticket["cif"]]["id"]

    # Empleado: su id es el código del cajero, así que no hace falta calcularlo
    if ticket["codigo_cajero"] not in tablas["empleado"]:
        tablas["empleado"][ticket["codigo_cajero"]] = {
            "nombre": ticket["nombre_cajero"],
            "sucursal_id": id_sucursal,
        }

    if ticket["forma_pago"] not in tablas["forma_pago"]:
        tablas["forma_pago"][ticket["forma_pago"]] = len(tablas["forma_pago"]) + 1

    for producto in ticket["productos"]:
        if producto["descripcion"] not in tablas["producto"]:
            # El ticket no trae el precio por unidad, así que lo calculamos: importe / cantidad.
            # Se guarda el del primer ticket en que aparece el producto.
            tablas["producto"][producto["descripcion"]] = {
                "id": len(tablas["producto"]) + 1,
                "precio": round(producto["importe"] / producto["cantidad"], 2),
            }

    tablas["ticket"][ticket["numero"]] = ticket


# ---------------------------------------------------------------------------
# 3. ESCRIBIR EL ARCHIVO SQL
# ---------------------------------------------------------------------------

def texto_sql(valor):
    """Prepara un texto para meterlo en un INSERT: lo pone entre comillas simples y duplica las
    comillas que lleve dentro (en SQL, '' significa una comilla). Así un nombre como O'Brien
    no rompe la consulta."""
    return "'" + str(valor).replace("'", "''") + "'"


def generar_sql(tablas, nombre_archivo):
    """Escribe en el archivo un INSERT por cada registro de cada tabla y devuelve la lista de
    sentencias, para poder ejecutarlas después en MySQL."""
    sentencias = ["USE tickets_db;"]  # lista de líneas; al final se escriben todas juntas

    # Primero vaciamos las tablas, para que la base de datos quede SOLO con los tickets válidos
    # de esta ejecución: si un ticket se ha descartado, desaparece; cuando se arregla, vuelve.
    # Se borra en orden inverso al de los INSERT, porque MySQL no deja borrar algo a lo que
    # todavía apunta una clave foránea (un ticket que aún tiene líneas, por ejemplo).
    for tabla in ["ticket_linea", "ticket", "producto", "forma_pago", "empleado", "sucursal"]:
        sentencias.append(f"DELETE FROM {tabla};")

    # El orden importa por las claves foráneas: primero las tablas de las que dependen las demás.
    # (un empleado necesita su sucursal, un ticket su empleado y su forma de pago, una línea su
    # ticket y su producto)
    for cif, s in tablas["sucursal"].items():  # items() da cada pareja clave-valor
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
        # Si no hay autorización (pago en efectivo) se escribe NULL sin comillas: "sin valor"
        if t["autorizacion"] is None:
            autorizacion = "NULL"
        else:
            autorizacion = texto_sql(t["autorizacion"])
        # strftime hace lo contrario que strptime: convierte la fecha en texto con el formato de MySQL
        fecha_hora = t["fecha_hora"].strftime("%Y-%m-%d %H:%M:%S")
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
        # "\n".join() une todas las sentencias en un solo texto, una por línea
        archivo.write("\n".join(sentencias) + "\n")

    return sentencias


# ---------------------------------------------------------------------------
# 4. CARGAR EN MYSQL
# ---------------------------------------------------------------------------

def cargar_en_mysql(sentencias):
    """Ejecuta las sentencias en MySQL. Devuelve True si se han cargado y False si ha fallado algo."""
    try:
        conexion = mysql.connector.connect(**DATOS_CONEXION)  # ** "desempaqueta" el diccionario: host=..., user=...
    except mysql.connector.Error as error:
        avisar_error(f"No se ha podido conectar a MySQL: {error}")
        avisar_error("¿Está MySQL arrancado en XAMPP y has creado la base de datos con schema.sql?")
        return False

    cursor = conexion.cursor()  # el objeto con el que lanzamos las consultas
    try:
        for sentencia in sentencias:
            cursor.execute(sentencia)
        # Transacción: los DELETE y los INSERT no se guardan de verdad hasta el commit(),
        # y se guardan todos a la vez. Así nunca se queda la base de datos a medias.
        conexion.commit()
        return True
    except mysql.connector.Error as error:
        # rollback() deshace todo lo que se había hecho desde el último commit: si falla un
        # INSERT, la base de datos se queda exactamente como estaba antes de ejecutar el script.
        conexion.rollback()
        avisar_error(f"Error al cargar los datos en MySQL, no se ha cambiado nada: {error}")
        return False
    finally:
        # finally se ejecuta siempre, haya error o no: cerramos lo que hemos abierto
        cursor.close()
        conexion.close()


# ---------------------------------------------------------------------------
# 5. PROGRAMA PRINCIPAL
# ---------------------------------------------------------------------------

def main():
    """Comprueba el argumento, lee los tickets de la carpeta, genera insert_ticket.sql y lo carga en MySQL."""
    # Primera línea de cada ejecución en el log, para separarla de las anteriores.
    # " ".join(sys.argv) vuelve a juntar el comando tal como se escribió en la terminal.
    escribir_log("INFO", f"===== Inicio: {' '.join(sys.argv)} =====")

    # sys.argv[0] es el nombre del script; la carpeta tiene que venir en sys.argv[1]
    if len(sys.argv) != 2:
        avisar_error("Uso: python build_insert_from_tickets.py <carpeta_de_tickets>")
        sys.exit(1)  # 1 = el programa termina con error (0 sería que todo ha ido bien)

    carpeta = sys.argv[1]
    if not os.path.isdir(carpeta):  # isdir() es True si la ruta existe y es una carpeta
        avisar_error(f"La carpeta '{carpeta}' no existe.")
        sys.exit(1)

    tablas = crear_tablas_vacias()

    # sorted() para leer siempre en el mismo orden (001, 002...). Importa: el precio de cada
    # producto se toma del primer ticket donde aparece, y Windows no garantiza ningún orden.
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.endswith(".txt"):
            continue  # continue salta al siguiente archivo sin hacer nada con este

        # Cada ticket va dentro de su propio try: si uno está mal, se avisa, se descarta
        # y el programa sigue con los demás en lugar de pararse entero.
        # ValueError: los que lanzamos nosotros, o un float()/int() con texto que no es número.
        # IndexError: un archivo cortado (por ejemplo, con menos de 3 líneas: lineas[2] no existe).
        try:
            ticket = leer_ticket(os.path.join(carpeta, nombre))
            anadir_ticket(tablas, ticket)
            # Los tickets correctos solo van al log: en la terminal solo queremos el resumen
            escribir_log("INFO", f"{nombre}: correcto (ticket {ticket['numero']}, {len(ticket['productos'])} productos)")
        except (ValueError, IndexError) as error:
            avisar_error(f"{nombre}: descartado ({error})")

    sentencias = generar_sql(tablas, ARCHIVO_SALIDA)

    # Resumen en forma de lista: una línea por cada dato
    informar(f"- Tickets: {len(tablas['ticket'])}")
    informar(f"- Empleados: {len(tablas['empleado'])}")
    informar(f"- Productos: {len(tablas['producto'])}")
    informar(f"- Formas de pago: {len(tablas['forma_pago'])}")
    informar(f"Generado {ARCHIVO_SALIDA}")

    if cargar_en_mysql(sentencias):
        informar("Base de datos tickets_db actualizada")
    else:
        sys.exit(1)  # el .sql sí se ha generado, pero avisamos de que la carga ha fallado


# Solo se ejecuta main() si lanzamos este archivo directamente, no si otro script lo importa
if __name__ == "__main__":
    main()
