# Actividad 12 - Subir tickets de supermercado a MySQL

- **Asignatura:** Python (2º DAW)
- **Alumno:** Jorge Ruiz
- **Fecha de entrega:** (pendiente)

## Enunciado (resumido)

Hacer un script en Python que lea los 20 tickets de "Supermercados El Ahorro" de la carpeta
`data_tikets` y guarde sus datos en una base de datos MySQL:

- Tabla `tickets`: un registro por ticket (número, fecha, hora, cajero, subtotal, IVA, total y forma de pago).
- Tabla `lineas_ticket`: un registro por cada producto de cada ticket (cantidad, descripción e importe),
  relacionado con su ticket mediante una clave foránea.

Si el script se ejecuta más de una vez, los tickets que ya están en la base de datos no se repiten.

> No había enunciado escrito. Si el profesor pide algo distinto, se adapta.

## Estructura

| Archivo / carpeta | Qué es |
|---|---|
| `data_tikets/` | Los 20 tickets (`factura_001.txt` … `factura_020.txt`) |
| `crear_bd.sql` | Crea la base de datos `supermercado` y sus dos tablas |
| `subir_tickets.py` | Lee los tickets y los inserta en MySQL |

## Cómo ejecutarlo

1. Arranca **MySQL** desde el panel de XAMPP (botón *Start*).
2. Instala el conector de MySQL para Python (solo la primera vez):
   ```powershell
   python -m pip install mysql-connector-python
   ```
3. Crea la base de datos (solo la primera vez). Puedes hacerlo de dos formas:
   - En phpMyAdmin (`http://localhost/phpmyadmin`) → pestaña **Importar** → elegir `crear_bd.sql`.
   - O desde la terminal, dentro de esta carpeta:
     ```powershell
     C:\xamppp\mysql\bin\mysql.exe -u root -e "source crear_bd.sql"
     ```
4. Ejecuta el script desde esta carpeta:
   ```powershell
   $env:PYTHONUTF8=1
   python subir_tickets.py
   ```
5. Comprueba los datos en phpMyAdmin, en la base de datos `supermercado`.
