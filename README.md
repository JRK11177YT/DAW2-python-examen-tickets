# Examen Python - Generador SQL de tickets

- **Asignatura:** Python (2º DAW)
- **Alumno:** Jorge Ruiz
- **Fecha de entrega:** (pendiente)

## Qué hace

`build_insert_from_tickets.py` lee todos los tickets `.txt` de la carpeta que recibe como argumento,
comprueba que cada uno es correcto y genera `insert_ticket.sql` con los `INSERT` de las 6 tablas de
la base de datos `tickets_db`:

| Tabla | Qué guarda | Sin repetir por |
|---|---|---|
| `sucursal` | Nombre, dirección, CIF y teléfono de la tienda | CIF |
| `empleado` | Los cajeros (su id es el código del ticket) | código de cajero |
| `forma_pago` | TARJETA, EFECTIVO... | nombre |
| `producto` | Cada producto con su precio por unidad o por kg | descripción |
| `ticket` | Cabecera y totales de cada ticket | número de ticket |
| `ticket_linea` | Cada producto de cada ticket | (ticket, producto) |

Si un ticket tiene algún error (CIF incorrecto, fecha que no existe, cuentas que no cuadran, número
repetido...), se avisa por pantalla, se descarta y el programa sigue con los demás.

## Estructura

| Archivo / carpeta | Qué es |
|---|---|
| `data_tikets/` | Los 20 tickets (`factura_001.txt` … `factura_020.txt`) |
| `schema.sql` | Crea la base de datos `tickets_db` y sus 6 tablas |
| `build_insert_from_tickets.py` | El script |
| `insert_ticket.sql` | Se genera al ejecutar el script |
| `tickets.log` | Se genera al ejecutar el script: historial de todas las ejecuciones con fecha y hora (tickets correctos, descartados y por qué, resumen y carga en MySQL) |

## Cómo ejecutarlo

Desde la terminal, dentro de esta carpeta:

```powershell
$env:PYTHONUTF8=1
python build_insert_from_tickets.py data_tikets
```

Sale este resumen y se crea `insert_ticket.sql`:

```
- Tickets: 20
- Empleados: 7
- Productos: 20
- Formas de pago: 2
Generado insert_ticket.sql
Base de datos tickets_db actualizada
```

## Cómo cargarlo en MySQL

El script **carga los datos en MySQL él solo**, cada vez que se ejecuta. Solo hace falta, con MySQL
arrancado en XAMPP:

1. **La primera vez**, crear la base de datos y sus tablas con `schema.sql`:
   - en phpMyAdmin (`http://localhost/phpmyadmin`) → pestaña **Importar** → `schema.sql`,
   - o desde la terminal: `C:\xamppp\mysql\bin\mysql.exe -u root -e "source schema.sql"`
2. Ejecutar el script como se explica arriba. Al final dice `Base de datos tickets_db actualizada`.

Cada carga empieza vaciando las 6 tablas y después inserta solo los tickets válidos. Así la base de
datos queda siempre igual que la carpeta: si un ticket se descarta por un error, desaparece de la
base de datos, y cuando se arregla vuelve a entrar. Todo va en una transacción: si algo falla a
medias, no se cambia nada.

Si MySQL está parado, el script genera igualmente `insert_ticket.sql` y avisa de que no ha podido
conectar.
