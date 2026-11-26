// Pinos e recursos de cada placa suportada (ver docs/hardware.md).
#pragma once

#if defined(PLACA_DEVKIT_V1)
  #define PLACA_NOME        "ESP32 DevKit V1"
  // LED azul da placa: luz de aviso.
  #define PINO_LED          2
  // Tela SPI (VSPI).
  #define PINO_TELA_SCK     18
  #define PINO_TELA_MOSI    23
  #define PINO_TELA_CS      5
  #define PINO_TELA_DC      16
  #define PINO_TELA_RST     17
  #define PINO_TELA_BL      4
  // Amplificador I2S (MAX98357A).
  #define PINO_I2S_BCLK     26
  #define PINO_I2S_LRC      25
  #define PINO_I2S_DIN      27
  // Botões (para o GND, com pull-up interno).
  #define PINO_BOTAO_A      32
  #define PINO_BOTAO_B      33
#else
  #error "Placa não definida: use uma env do platformio.ini (ex.: -D PLACA_DEVKIT_V1)"
#endif

#define NOME_REDE     "pets"         // pets.local (mDNS) e hostname
#define REDE_CONFIG   "pets-config"  // rede do portal de configuração do Wi-Fi
#define PORTA_HTTP    8765           // a mesma do simulador
#define VERSAO        "0.1.0"
