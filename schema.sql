-- Alumno: Jorge Ruiz
-- Examen Python - Generador SQL de tickets
-- Crea la base de datos tickets_db con sus 6 tablas. Hay que ejecutarlo ANTES que insert_ticket.sql.

-- Borramos la base de datos si ya existía, para empezar siempre desde cero.
-- Así se puede repetir la prueba sin que los INSERT choquen con datos antiguos.
DROP DATABASE IF EXISTS tickets_db;
-- utf8mb4 para que se guarden bien las tildes, la ñ y el €
CREATE DATABASE tickets_db CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci;
USE tickets_db;

-- La tienda que aparece en la cabecera del ticket
CREATE TABLE sucursal (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    nombre     VARCHAR(100) NOT NULL,
    direccion  VARCHAR(150) NOT NULL,
    cif        VARCHAR(9)   NOT NULL UNIQUE,  -- UNIQUE: no puede haber dos sucursales con el mismo CIF
    telefono   VARCHAR(15)                    -- texto y no número: un teléfono no se suma ni se resta
);

-- Los cajeros. El id es el código que sale en el ticket ("Cajero: 015" -> 15)
CREATE TABLE empleado (
    id           INT PRIMARY KEY,
    nombre       VARCHAR(100) NOT NULL,
    sucursal_id  INT NOT NULL,
    FOREIGN KEY (sucursal_id) REFERENCES sucursal(id)
);

-- Cada producto distinto una sola vez, con su precio por unidad (o por kg)
CREATE TABLE producto (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    descripcion  VARCHAR(100) NOT NULL UNIQUE,
    precio       DECIMAL(8,2) NOT NULL  -- DECIMAL para el dinero: guarda los céntimos exactos
);

-- TARJETA, EFECTIVO...
CREATE TABLE forma_pago (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    nombre  VARCHAR(20) NOT NULL UNIQUE
);

-- La cabecera y los totales de cada ticket. numero es el de "Ticket: 20010001"
CREATE TABLE ticket (
    numero         INT PRIMARY KEY,
    fecha_hora     DATETIME NOT NULL,      -- fecha y hora juntas: 2025-09-11 17:01:00
    empleado_id    INT NOT NULL,
    subtotal       DECIMAL(8,2) NOT NULL,
    iva            DECIMAL(8,2) NOT NULL,
    total          DECIMAL(8,2) NOT NULL,
    forma_pago_id  INT NOT NULL,
    autorizacion   VARCHAR(10) NULL,       -- NULL porque los pagos en efectivo no tienen autorización
    FOREIGN KEY (empleado_id)   REFERENCES empleado(id),
    FOREIGN KEY (forma_pago_id) REFERENCES forma_pago(id)
);

-- Una fila por cada producto de cada ticket
CREATE TABLE ticket_linea (
    ticket_numero  INT NOT NULL,
    producto_id    INT NOT NULL,
    cantidad       DECIMAL(8,3) NOT NULL,  -- 3 decimales por los productos al peso (2.500 kg)
    importe        DECIMAL(8,2) NOT NULL,
    -- Clave primaria de dos columnas: un mismo producto solo puede salir una vez en cada ticket
    PRIMARY KEY (ticket_numero, producto_id),
    FOREIGN KEY (ticket_numero) REFERENCES ticket(numero),
    FOREIGN KEY (producto_id)   REFERENCES producto(id)
);
