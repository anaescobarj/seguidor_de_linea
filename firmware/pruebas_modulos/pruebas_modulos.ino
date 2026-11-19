// =====================================================================
//  pruebas_modulos.ino – Pruebas del robot módulo por módulo (montaje)
//
//  Cargar ANTES del firmware final. Abrir el Monitor Serie a 115200 baudios
//  (fin de línea: "Nueva línea") y enviar el número de la prueba:
//
//    1  Escáner I2C            (espera 0x0D brújula y 0x29 color)
//    2  Motores                (izq. adelante/atrás, der. adelante/atrás)
//    3  Sensores de línea      (TCRT5000, 10 s en vivo)
//    4  Brújula QMC5883L       (crudos y rumbo, 15 s; gire el robot a mano)
//    5  Sensor de color        (RGBC y cromaticidad, 15 s)
//    6  Ultrasonido + servo    (barrido 20°–160° con distancias)
//    7  Batería y termistor    (voltaje y temperatura, 10 s)
//    8  Todo en vivo           (resumen cada 250 ms, 20 s)
//    0  Parar motores
//
//  Pines: copia de firmware/robot_esp32/config.h (mantener sincronizados).
//  Placa: ESP32 Dev Module – arduino-esp32 core >= 3.0
// =====================================================================
#include <Wire.h>

// --- pines (iguales a config.h) ---
#define PIN_PWMA 25
#define PIN_AIN1 26
#define PIN_AIN2 27
#define PIN_PWMB 14
#define PIN_BIN1 16
#define PIN_BIN2 32
#define PIN_STBY 13
#define PIN_SDA 21
#define PIN_SCL 22
#define PIN_COLOR_LED 4
#define PIN_TRIG 18
#define PIN_ECHO 19
#define PIN_SERVO 23
#define PIN_IR_L 34
#define PIN_IR_C 35
#define PIN_IR_R 39
#define PIN_VBAT 36
#define PIN_NTC 33
#define PIN_LED 2

#define VBAT_RATIO ((100.0f + 33.0f) / 33.0f)
#define QMC_ADDR 0x0D
#define TCS_ADDR 0x29

// ---------------------------------------------------------------------
static void motor(int pwm, int in1, int in2, float v) {
  int duty = (int)(fabsf(v) * 0.8f * 1023);
  digitalWrite(in1, v > 0 ? HIGH : LOW);
  digitalWrite(in2, v < 0 ? HIGH : LOW);
  ledcWrite(pwm, v == 0 ? 0 : duty);
}
static void motors(float l, float r) {
  motor(PIN_PWMA, PIN_AIN1, PIN_AIN2, l);
  motor(PIN_PWMB, PIN_BIN1, PIN_BIN2, r);
}

static void servoWrite(int deg) {
  uint32_t us = map(constrain(deg, 0, 180), 0, 180, 500, 2400);
  ledcWrite(PIN_SERVO, (us * 16383UL) / 20000UL);
}

static float sonarCm() {
  digitalWrite(PIN_TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long t = pulseIn(PIN_ECHO, HIGH, 25000UL);
  return t == 0 ? -1 : t * 0.0343f / 2.0f;
}

static void wr(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr); Wire.write(reg); Wire.write(val); Wire.endTransmission();
}
static int16_t rd16() { uint8_t lo = Wire.read(); uint8_t hi = Wire.read(); return (int16_t)(lo | (hi << 8)); }

static bool qmcRead(int16_t& x, int16_t& y, int16_t& z) {
  Wire.beginTransmission(QMC_ADDR); Wire.write(0x00);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((uint8_t)QMC_ADDR, (uint8_t)6) != 6) return false;
  x = rd16(); y = rd16(); z = rd16();
  return true;
}

static bool tcsRead(uint16_t& c, uint16_t& r, uint16_t& g, uint16_t& b) {
  Wire.beginTransmission(TCS_ADDR); Wire.write(0x80 | 0x20 | 0x14);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((uint8_t)TCS_ADDR, (uint8_t)8) != 8) return false;
  c = rd16(); r = rd16(); g = rd16(); b = rd16();
  return true;
}

static float ntcC(bool& ok) {
  uint32_t mv = 0;
  for (int i = 0; i < 8; i++) mv += analogReadMilliVolts(PIN_NTC);
  float v = mv / 8.0f;
  ok = v > 50 && v < 3250;
  if (!ok) return NAN;
  float r = 10000.0f * v / (3300.0f - v);
  return 1.0f / (1.0f / 298.15f + logf(r / 10000.0f) / 3950.0f) - 273.15f;
}

static float vbat() { return analogReadMilliVolts(PIN_VBAT) / 1000.0f * VBAT_RATIO; }

static bool abortRequested() {   // cualquier tecla detiene la prueba en curso
  if (Serial.available()) { while (Serial.available()) Serial.read(); motors(0, 0); return true; }
  return false;
}

// ---------------------------------------------------------------------
static void testI2C() {
  Serial.println("Escaneando I2C...");
  int n = 0;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      n++;
      Serial.printf("  0x%02X %s\n", a, a == QMC_ADDR ? "<- brujula QMC5883L" :
                                         a == TCS_ADDR ? "<- color TCS34725" :
                                         a == 0x1E ? "<- HMC5883L (otro chip: cambiar driver)" : "");
    }
  }
  if (!n) Serial.println("  Nada. Revise SDA=21, SCL=22, 3V3 y GND.");
}

static void testMotors() {
  struct { const char* name; float l, r; } steps[] = {
    {"IZQUIERDA adelante", 0.5f, 0}, {"IZQUIERDA atras", -0.5f, 0},
    {"DERECHA adelante", 0, 0.5f},   {"DERECHA atras", 0, -0.5f},
    {"AMBOS adelante (debe ir recto)", 0.5f, 0.5f}, {"GIRO en el sitio a la derecha", 0.5f, -0.5f}};
  Serial.println("Robot LEVANTADO (ruedas al aire). Cualquier tecla aborta.");
  for (auto& s : steps) {
    Serial.printf("  %s...\n", s.name);
    motors(s.l, s.r);
    for (int i = 0; i < 15; i++) { delay(100); if (abortRequested()) return; }
    motors(0, 0); delay(400);
  }
  Serial.println("Si un lado gira al reves: intercambie sus 2 cables en AO1/AO2 o BO1/BO2.");
}

static void testLine() {
  Serial.println("1 = superficie oscura. Pase la cinta bajo cada sensor (10 s).");
  for (int i = 0; i < 40 && !abortRequested(); i++) {
    Serial.printf("  I:%d  C:%d  D:%d\n", digitalRead(PIN_IR_L), digitalRead(PIN_IR_C), digitalRead(PIN_IR_R));
    delay(250);
  }
  Serial.println("Ajuste el potenciometro azul de cada modulo hasta que cambie limpio entre cinta y piso.");
}

static void testCompass() {
  wr(QMC_ADDR, 0x0B, 0x01); wr(QMC_ADDR, 0x09, 0x1D);
  Serial.println("Gire el robot lentamente 360 grados (15 s).");
  int16_t mnx = 32767, mxx = -32768, mny = 32767, mxy = -32768;
  for (int i = 0; i < 60 && !abortRequested(); i++) {
    int16_t x, y, z;
    if (!qmcRead(x, y, z)) { Serial.println("  Sin respuesta en 0x0D."); return; }
    mnx = min(mnx, x); mxx = max(mxx, x); mny = min(mny, y); mxy = max(mxy, y);
    float h = atan2f(y, x) * 180 / PI; if (h < 0) h += 360;
    Serial.printf("  x=%6d y=%6d z=%6d  rumbo(sin calibrar)=%5.1f\n", x, y, z, h);
    delay(250);
  }
  Serial.printf("Rango X [%d, %d]  Y [%d, %d]\n", mnx, mxx, mny, mxy);
  Serial.println("Ambos rangos deben ser parecidos y > 500. Si un eje casi no cambia, aleje el modulo de motores/tornillos.");
}

static void testColor() {
  wr(TCS_ADDR, 0x80 | 0x01, 0xEB); wr(TCS_ADDR, 0x80 | 0x0F, 0x01);
  wr(TCS_ADDR, 0x80 | 0x00, 0x01); delay(3); wr(TCS_ADDR, 0x80 | 0x00, 0x03);
  digitalWrite(PIN_COLOR_LED, HIGH);
  Serial.println("Ponga el robot sobre cada color de la pista (15 s). Anote r,g,b,C de cada uno.");
  for (int i = 0; i < 60 && !abortRequested(); i++) {
    delay(250);
    uint16_t c, r, g, b;
    if (!tcsRead(c, r, g, b)) { Serial.println("  Sin respuesta en 0x29."); return; }
    float s = (float)r + g + b; if (s < 1) s = 1;
    Serial.printf("  C=%5u R=%5u G=%5u B=%5u  ->  r=%.2f g=%.2f b=%.2f\n", c, r, g, b, r / s, g / s, b / s);
  }
}

static void testSonar() {
  Serial.println("Barrido del servo con distancias (-1 = sin eco).");
  for (int a = 20; a <= 160; a += 20) {
    servoWrite(a); delay(400);
    Serial.printf("  servo %3d  ->  %6.1f cm\n", a, sonarCm());
    if (abortRequested()) break;
  }
  servoWrite(90);
  Serial.println("Ponga la mano a 20 cm al frente: debe leer ~20 cm.");
}

static void testPower() {
  for (int i = 0; i < 20 && !abortRequested(); i++) {
    bool ok; float t = ntcC(ok);
    if (ok) Serial.printf("  Bateria %.2f V   Temp. NTC %.1f C\n", vbat(), t);
    else    Serial.printf("  Bateria %.2f V   NTC desconectado o en corto (revise GPIO33)\n", vbat());
    delay(500);
  }
  Serial.println("Compare el voltaje con el multimetro; ajuste VBAT_RATIO en config.h si difiere > 0.1 V.");
}

static void testAll() {
  wr(QMC_ADDR, 0x0B, 0x01); wr(QMC_ADDR, 0x09, 0x1D);
  wr(TCS_ADDR, 0x80 | 0x01, 0xEB); wr(TCS_ADDR, 0x80 | 0x0F, 0x01);
  wr(TCS_ADDR, 0x80 | 0x00, 0x01); delay(3); wr(TCS_ADDR, 0x80 | 0x00, 0x03);
  for (int i = 0; i < 80 && !abortRequested(); i++) {
    int16_t x = 0, y = 0, z = 0; uint16_t c = 0, r = 0, g = 0, b = 0; bool ok;
    qmcRead(x, y, z); tcsRead(c, r, g, b);
    float h = atan2f(y, x) * 180 / PI; if (h < 0) h += 360;
    float t = ntcC(ok);
    Serial.printf("H=%5.1f  d=%5.1fcm  IR=%d%d%d  RGBC=%u,%u,%u,%u  V=%.2f  T=%.1f\n", h, sonarCm(),
                  digitalRead(PIN_IR_L), digitalRead(PIN_IR_C), digitalRead(PIN_IR_R), r, g, b, c, vbat(), t);
    delay(250);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_AIN1, OUTPUT); pinMode(PIN_AIN2, OUTPUT);
  pinMode(PIN_BIN1, OUTPUT); pinMode(PIN_BIN2, OUTPUT);
  pinMode(PIN_STBY, OUTPUT); digitalWrite(PIN_STBY, HIGH);
  ledcAttach(PIN_PWMA, 20000, 10); ledcAttach(PIN_PWMB, 20000, 10);
  motors(0, 0);
  pinMode(PIN_TRIG, OUTPUT); pinMode(PIN_ECHO, INPUT);
  ledcAttach(PIN_SERVO, 50, 14); servoWrite(90);
  pinMode(PIN_IR_L, INPUT); pinMode(PIN_IR_C, INPUT); pinMode(PIN_IR_R, INPUT);
  pinMode(PIN_COLOR_LED, OUTPUT); pinMode(PIN_LED, OUTPUT);
  analogSetPinAttenuation(PIN_VBAT, ADC_11db); analogSetPinAttenuation(PIN_NTC, ADC_11db);
  Wire.begin(PIN_SDA, PIN_SCL, 100000);
  delay(500);
  Serial.println("\n=== Pruebas de modulos ===");
  Serial.println("1 I2C | 2 Motores | 3 Linea | 4 Brujula | 5 Color | 6 Ultrasonido | 7 Bateria/NTC | 8 Todo | 0 Parar");
}

void loop() {
  digitalWrite(PIN_LED, (millis() / 500) % 2);
  if (!Serial.available()) return;
  char c = Serial.read();
  while (Serial.available()) Serial.read();
  switch (c) {
    case '1': testI2C(); break;
    case '2': testMotors(); break;
    case '3': testLine(); break;
    case '4': testCompass(); break;
    case '5': testColor(); break;
    case '6': testSonar(); break;
    case '7': testPower(); break;
    case '8': testAll(); break;
    case '0': motors(0, 0); Serial.println("Motores detenidos."); break;
    default: return;
  }
  Serial.println("\nListo. Elija otra prueba (1-8, 0).");
}
