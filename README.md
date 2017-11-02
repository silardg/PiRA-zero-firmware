# PiRA-zero-firmware
Firmware for PiRa Zero board implementing hardware interface functions.

## Software support for hardware features
 * USB charger BQ24296 I2c
 * RTC DS3231 I2C
 * ADC MCP3021 I2C
 * Display SSD1306 I2C
 * RFM95 Lora SPI
 
## Board support package
 * GPIO for power scheduling
 * GPIO for power output
 
### Power scheduling
On boot:
 1. Detect power-up trigger
  * if BCM17 (Timer-EN) is LOW then
   * Self-enable, if reboot and BCM18 is HIGH
   * else Timer enable
   * corner case, reboot due to self enable and timer at the same time, must clear timer in any case
  * if BCM 22 is LOW then
   * RTC enable if alarm is high, check via I2C
   * else enabled due to charging
  * none of the above, handle by resetting all timing soruces
 1. Self-enable GPIO BCM 18 to stay turned on
 1. Reset timing sources
  * assert Done for Timer on BCM27
  * reset RTC alarms
 During operation:
  1. monitor BCM17 and BCM22 for changes, repeat Detect power-up if needed
 On Shutdown:
  1. Check RTC wakeup is at least 30s away from now.
  1. do shutdown
  

### Application specific features
 1. Capture camera image and check for daylight/minimal light in image (maybe https://github.com/pageauc/pi-timolo)
 1. WiFi connect and hotspot https://github.com/resin-io/resin-wifi-connect
 1. Capture video for some time if sufficient light is available
 1. Measure distance with MB7092XL-MaxSonar-WRMA1
 1. Send data to TheThingsNetwork
 1. Send data over RockBlock Iridium modem
