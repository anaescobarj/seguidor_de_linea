# Guía de montaje del robot

Orden recomendado: **mecánica → potencia → control → sensores**, probando cada módulo apenas
se conecta con el sketch `firmware/pruebas_modulos/pruebas_modulos.ino`. Si algo falla, falla
solo lo último que se conectó.

> Las conexiones de esta guía corresponden a `firmware/robot_esp32/config.h` (versión con termistor:
> **BIN1 en GPIO16** y **NTC en GPIO33**). Si el informe o el esquema muestran BIN1 en GPIO33,
> vale lo de esta guía.

---

## 0. Antes de empezar

### Lista de materiales (marcar al tener)

| ✓ | Cant. | Componente | Nota |
|---|---|---|---|
| ☐ | 1 | ESP32 DevKit V1 (38 pines, módulo WROOM) | WROVER no: usa GPIO16 para PSRAM |
| ☐ | 1 | Puente H TB6612FNG | |
| ☐ | 4 | Motorreductor TT 1:48 + rueda 65 mm | |
| ☐ | 4 | Capacitor cerámico 100 nF | uno soldado en cada motor |
| ☐ | 1 | GY-271 (QMC5883L) | |
| ☐ | 1 | TCS34725 con LED | |
| ☐ | 1 | HC-SR04 + servo SG90 | |
| ☐ | 3 | Módulo TCRT5000 con comparador (salida D0) | |
| ☐ | 1 | Termistor NTC 10 kΩ B3950 (encapsulado epoxi o de cable) | |
| ☐ | 2 | Celdas 18650 + portapilas 2S + BMS 2S | celdas del mismo lote y carga |
| ☐ | 1 | Regulador MP1584 (step-down ajustable) | |
| ☐ | 1 | Interruptor + portafusible + fusible 3 A lento | |
| ☐ | 2 | Capacitor electrolítico 470 µF / 16 V | |
| ☐ | — | Resistencias: 100 kΩ, 33 kΩ, 10 kΩ, 2 kΩ, 1 kΩ | divisores |
| ☐ | 1 | PCB perforada ~7×5 cm, headers hembra, borneras | |
| ☐ | 6 | Separadores M3 × 45 mm + tornillos/tuercas M3 | |
| ☐ | — | Cable 22 AWG (potencia) y 26 AWG / dupont (señales), termoencogible | |
| ☐ | — | Cinta aislante negra de 19 mm (línea guía de la pista) | y un rollo blanco para la sección negra |

Las **pistas** (planos a escala, tablas de trazado y cantidades de cartulina) están en
[`docs/pistas/Plantillas_Pistas.pdf`](pistas/Plantillas_Pistas.pdf).

### Piezas a fabricar

| Pieza | Archivo | Proceso |
|---|---|---|
| Placa base | `hardware/cad/placa_base.dxf` | Corte láser, MDF 3 mm |
| Placa superior | `hardware/cad/placa_superior.dxf` | Corte láser, acrílico 3 mm |
| Soporte sensores de piso | `hardware/cad/soporte_sensores.stl` | PLA, 0.2 mm, 30 % relleno |
| Mástil de la brújula | `hardware/cad/mastil.stl` | PLA |
| Escuadra del ultrasonido | `hardware/cad/soporte_sonar.stl` | PLA |

### Herramientas
Cautín y estaño, multímetro (**imprescindible**), destornilladores, pinzas, pistola de silicona,
bridas, cinta Kapton o de aislar.

### Seguridad con 18650
- Cargue las celdas con cargador de litio y **verifique que ambas estén a ±0.05 V** antes de ponerlas en serie.
- Nunca suelde directamente sobre la celda. Use portapilas.
- No deje el robot cargando sin supervisión. Si una celda se calienta o se hincha, retírela.

---

## 1. Preparar y probar el ESP32 (sin nada conectado)

1. Arduino IDE → *Boards Manager* → **esp32 by Espressif ≥ 3.0**. Placa: **ESP32 Dev Module**.
2. Cargue `firmware/pruebas_modulos/pruebas_modulos.ino`, abra el Monitor Serie a **115200** con
   fin de línea *Nueva línea*.
3. Debe aparecer el menú y el LED azul debe parpadear. Envíe `1`: el escáner I2C no debe encontrar nada (todavía).

✅ **Control:** el ESP32 carga código y responde al menú.

---

## 2. Mecánica base

1. **Motores:** suelde dos cables (~15 cm, rojo/negro) y un **capacitor de 100 nF entre los
   terminales** de cada motor. Proteja con termoencogible.
2. Atornille los 4 motores bajo la placa base (2 tornillos M3 cada uno) con el eje hacia afuera.
   Lleve los cables por las ventanas centrales.
3. Ponga las ruedas a presión.
4. Atornille los **6 separadores** de 45 mm (aún sin la placa superior).

✅ **Control:** las ruedas giran libres a mano y el chasis apoya en las cuatro sin cojear.

---

## 3. Potencia (sin ESP32 ni sensores conectados)

```
(+) Portapilas 2S + BMS ── Interruptor ── Fusible 3 A ──┬── C1 470 µF ── GND
                                                        ├── VM del TB6612
                                                        ├── VIN MP1584 ── VOUT = +5 V ── C2 470 µF ── GND
                                                        └── R1 100 k ──┬── GPIO36 (VBAT)
                                                                       └── R2 33 k ── GND
```

1. Monte el portapilas y el BMS sobre la placa base (centro) con silicona o bridas.
2. Cablee interruptor y fusible en el **positivo**.
3. **Ajuste el MP1584 antes de conectar nada a su salida:** encienda, mida VOUT con el multímetro
   y gire el potenciómetro hasta **5.0 V**. Apague.
4. Haga en la PCB perforada los rieles **+7.4 V**, **+5 V**, **+3V3** y **GND** común, con C1 y C2.
5. Suelde el divisor **R1 100 kΩ / R2 33 kΩ** (nodo → GPIO36).

✅ **Control con multímetro (sin ESP32 puesto):**
- Riel +7.4 V: 7.4–8.4 V. Riel +5 V: 4.9–5.1 V.
- Nodo VBAT: ≈ 0.248 × V<sub>bat</sub> (≈ 2.0 V con batería llena).
- No hay continuidad entre +7.4 V y GND, ni entre +5 V y GND.

---

## 4. ESP32 y puente H

1. Suelde headers hembra en la PCB y ponga el ESP32 en ellos (así se puede retirar).
2. **ESP32 VIN ← +5 V**, **GND ← GND**. El pin **3V3** del ESP32 alimenta el riel +3V3.
3. Conecte el TB6612FNG:

| TB6612 | Conectar a |
|---|---|
| PWMA, AIN1, AIN2 | GPIO25, GPIO26, GPIO27 |
| PWMB, **BIN1**, BIN2 | GPIO14, **GPIO16**, GPIO32 |
| STBY | GPIO13 |
| VCC | +3V3 |
| VM | +7.4 V |
| GND (los 3 pines) | GND |
| AO1/AO2 | 2 motores **izquierdos** en paralelo |
| BO1/BO2 | 2 motores **derechos** en paralelo |

> Motores del mismo lado en paralelo: rojo con rojo, negro con negro. Si al probar una rueda gira
> al revés que su compañera, invierta solo los cables de ese motor.

4. Encienda la batería con el USB conectado y envíe `2` (**prueba de motores**) con el robot
   **levantado**.

✅ **Control:**
- Izquierda adelante → giran las dos ruedas izquierdas hacia adelante (y así con cada paso).
- «Ambos adelante»: las 4 hacia adelante. Si un lado va al revés, intercambie AO1↔AO2 (o BO1↔BO2).
- El ESP32 **no se reinicia** al arrancar los motores. Si se reinicia: revise C1/C2, el grosor
  de los cables de potencia y que el GND sea común.

---

## 5. Sensores de piso (línea y color)

1. Atornille el **soporte impreso** en la ventana frontal de la placa base.
2. **3× TCRT5000** en la repisa (izq., centro, der.), a **8 mm del piso**:
   VCC → +3V3, GND → GND, D0 → **GPIO34 (izq.)**, **GPIO35 (centro)**, **GPIO39 (der.)**.
3. **TCS34725** en la repisa baja, a **5 mm del piso**, dentro del faldón:
   VIN → +3V3, GND → GND, SDA → GPIO21, SCL → GPIO22, LED → GPIO4.
4. Envíe `1`: debe aparecer **0x29**.
5. Envíe `3` y pase la cinta negra bajo cada TCRT5000. **Ajuste el potenciómetro azul** de cada
   módulo hasta que marque 1 sobre la cinta y 0 sobre el piso, sin parpadeos.
6. Envíe `5` y ponga el sensor sobre cada color de la pista. Anote los valores (sirven para calibrar).

✅ **Control:** cada sensor cambia limpio entre cinta y piso. Los 6 colores dan valores r, g, b
distinguibles. El negro tiene C bajo y el blanco C alto.

---

## 6. Placa superior: servo y ultrasonido

1. Atornille el **SG90** en su ventana (cuerpo hacia abajo, eje hacia arriba).
2. Pegue la **escuadra impresa** al horn del servo y monte el HC-SR04 en ella.
3. Servo: señal → **GPIO23**, + → +5 V, − → GND.
4. HC-SR04: VCC → +5 V, GND → GND, TRIG → **GPIO18**,
   ECHO → **R3 1 kΩ → nodo → GPIO19**, con **R4 2 kΩ del nodo a GND**. ⚠️ El ECHO da 5 V:
   sin el divisor se puede dañar el ESP32.
5. Antes de cerrar, pase todos los cables por las ventanas pasacables. Luego ponga la placa
   superior sobre los separadores.
6. Envíe `6`: el servo hace un barrido y muestra la distancia en cada ángulo.

✅ **Control:** con la mano a 20 cm al frente lee ≈ 20 cm. El servo no vibra en reposo y no
golpea nada en los extremos (20° y 160°).

---

## 7. Brújula en el mástil

1. Atornille el **mástil de PLA** en la parte trasera de la placa superior con tornillos **de nylon o de latón**.
   El acero cerca del magnetómetro distorsiona la lectura.
2. Pase los 4 cables del GY-271 por dentro del mástil y fije el módulo arriba, **con la flecha X apuntando
   al frente del robot**.
3. VCC → +3V3, GND → GND, SDA → GPIO21, SCL → GPIO22 (mismo bus que el sensor de color).
4. Envíe `1`: debe aparecer **0x0D y 0x29**. Si aparece 0x1E, el módulo trae un HMC5883L y hay que cambiar el driver.
5. Envíe `4` y gire el robot 360° lentamente sobre el piso.

✅ **Control:** el rumbo recorre 0–360° sin saltos raros. Los rangos de X e Y son parecidos.
Si un eje casi no cambia, hay hierro cerca: aleje cables y tornillos.

---

## 8. Termistor de la batería

```
+3V3 ── R5 10 kΩ ──┬── GPIO33
                   └── NTC 10 kΩ ── GND
```

1. Pegue el NTC **en contacto con las celdas**, entre las dos, con cinta Kapton.
2. Suelde R5 en la PCB y lleve el NTC con dos cables hasta el nodo y GND.
3. Envíe `7`.

✅ **Control:** a temperatura ambiente marca 20–30 °C. Al apretarlo entre los dedos sube unos grados.
El voltaje de batería coincide con el multímetro (±0.1 V). Si no coincide, ajuste `VBAT_RATIO` en `config.h`.

---

## 9. Firmware final y calibración

1. Envíe `8` (todo en vivo) y verifique que todos los valores se mueven.
2. Cargue `firmware/robot_esp32/robot_esp32.ino`.
3. Conéctese a la red **ROBOT-ESP32** (clave `robot1234`) y abra `http://192.168.4.1` (control de respaldo),
   o ejecute la app: `cd app && streamlit run app.py`.
4. En la app, pestaña **⚙️ Calibración**:
   - **Calibrar brújula:** robot en el piso, lejos de metal. Gira 8 s.
   - **Colores:** ponga el sensor sobre cada color de la pista y pulse *Guardar referencia*.
5. Pruebe el modo manual con los botones y con la voz. Luego el modo **Autónomo** sobre una recta con cinta.

### Ajustes finos en `config.h`
| Síntoma | Parámetro |
|---|---|
| Va en curva cuando debería ir recto | `MOTOR_TRIM_L` / `MOTOR_TRIM_R` (ej. 0.95) |
| Oscila sobre la línea | bajar la ganancia 0.45 en `ST_SEGUIR` o `AUTO_BASE_SPEED` |
| Se sale en curvas cerradas | bajar `AUTO_BASE_SPEED` |
| Detecta obstáculos muy tarde / muy pronto | `OBSTACLE_CM` |
| El rumbo tiene un error fijo | `MAG_DECLINATION_DEG` |
| La línea se invierte (1 en el piso, 0 en la cinta) | `IR_ACTIVE_LEVEL` |

---

## Problemas comunes

| Problema | Causa probable | Solución |
|---|---|---|
| El ESP32 se reinicia al arrancar los motores | Caída de tensión / ruido | Capacitores 100 nF en motores, C1/C2, cables de potencia más gruesos, GND común en estrella |
| No carga el código | GPIO12 con nivel alto al arrancar, o falta mantener BOOT | Este diseño no usa GPIO12. Mantenga BOOT al conectar |
| El escáner I2C no encuentra nada | SDA/SCL invertidos o sin 3V3 | Revise pines 21/22 y alimentación |
| La brújula marca siempre parecido | Imán o tornillo de acero cerca | Use el mástil y tornillería de nylon, y recalibre |
| El ultrasonido da −1 | ECHO sin señal / divisor mal | Revise R3/R4 y TRIG = 18, ECHO = 19 |
| El voltaje de batería da 0 | Divisor sin conectar a GPIO36 (VP) | VP es el pin «SVP/36» del DevKit |
| La app no conecta | No está en la red ROBOT-ESP32 | Conecte el PC/celular a esa red. URL `http://192.168.4.1` |

---

## Registro de montaje (llenar durante la práctica)

| Fase | Fecha | Prueba | Resultado / observaciones |
|---|---|---|---|
| 1. ESP32 | | menú serie | |
| 2. Mecánica | | ruedas libres | |
| 3. Potencia | | 5.0 V, VBAT | |
| 4. Motores | | prueba `2` | |
| 5. Piso | | pruebas `3` y `5` | |
| 6. Ultrasonido | | prueba `6` | |
| 7. Brújula | | pruebas `1` y `4` | |
| 8. Termistor | | prueba `7` | |
| 9. Firmware final | | app + calibración | |
