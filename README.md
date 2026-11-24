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
| `tickets.log` | Se genera al ejecutar el script: historial de todas las ejecuciones con fecha y hora (tickets correctos, descartados y por qué, y resumen) |

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
```

## Cómo cargarlo en MySQL

Con MySQL arrancado en XAMPP:

1. **Solo la primera vez**, crear la base de datos y sus tablas con `schema.sql`.
2. **Cada vez que se ejecute el script**, cargar el `insert_ticket.sql` que genera.

- **phpMyAdmin** (`http://localhost/phpmyadmin`) → pestaña **Importar** → el archivo que toque.
- **O desde la terminal:**
  ```powershell
  C:\xamppp\mysql\bin\mysql.exe -u root -e "source schema.sql"
  C:\xamppp\mysql\bin\mysql.exe -u root --default-character-set=utf8mb4 -e "source insert_ticket.sql"
  ```

`insert_ticket.sql` empieza vaciando las 6 tablas y después inserta solo los tickets válidos. Así la
base de datos queda igual que la carpeta: si un ticket se descarta por un error, desaparece de la
base de datos, y cuando se arregla vuelve a entrar.
