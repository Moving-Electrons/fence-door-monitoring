import time
import board
import busio
from digitalio import DigitalInOut, Direction, Pull
import neopixel
from analogio import AnalogIn
import adafruit_rgbled
from adafruit_esp32spi import PWMOut
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager

#TEXT_URL = "http://wifitest.adafruit.com/testwifi/index.html"
#JSON_URL = "http://api.coindesk.com/v1/bpi/currentprice/USD.json"

POST_TIME = 60*60 # seconds.

# Digital input configuration
switch_1 = DigitalInOut(board.D6)
switch_1.direction = Direction.INPUT
switch_1.pull = Pull.UP
switch_2 = DigitalInOut(board.D9)
switch_2.direction = Direction.INPUT
switch_2.pull = Pull.UP


vbat_pin = AnalogIn(board.VOLTAGE_MONITOR)

def get_voltage(pin):
    # Theoretical:
    #return ((pin.value * 3.3) / 65536) * 2

    # As measured on the Batt pin with tester:
    return ((pin.value * 3.3) / 62620) * 2
 
# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise


# Defining neopixel on M4 Express board
m4_neopixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
m4_neopixel.brightness = 0.2

# Pins to be used for AirLift Featherwing
esp32_cs = DigitalInOut(board.D13)
esp32_ready = DigitalInOut(board.D11)
esp32_reset = DigitalInOut(board.D12)
 
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)


# Using RGB LED on Airlift as Status Light
RED_LED = PWMOut.PWMOut(esp, 26)
GREEN_LED = PWMOut.PWMOut(esp, 27)
BLUE_LED = PWMOut.PWMOut(esp, 25)
status_light = adafruit_rgbled.RGBLED(RED_LED, BLUE_LED, GREEN_LED)



def post_adafruit(feed, data):

	while True:
	    try:
	        
	        print("Posting data to adafruit.io... ")
	        
	        payload = {"value": data}
	        response = wifi.post(
	            "https://io.adafruit.com/api/v2/"
	            + secrets["aio_username"]
	            + "/feeds/"
	            + feed
	            + "/data",
	            json=payload,
	            headers={"X-AIO-KEY": secrets["aio_key"]},
	        )
	        print(f'Adafruit.io response: {response.json()}')
	        response.close()
	        print('OK')
	        break

	    except (ValueError, RuntimeError) as e:
	        print("Failed to get data, retrying\n", e)
	        wifi.reset()
	        continue

	response = None
	return

def post_homebridge(sensor, state):
	'''
	Sends data to Homebridge.
	Parameter:
	sensor: sensor ID as defined on the Homebridge configuration file. String.
	state: can be either 'true' or 'false'.
	'''

	while True:
	    try:
	        
	        payload = f"http://{secrets['server_ip']}/?accessoryId={sensor}&state={state}"
	        response = wifi.get(payload)
	        print(f'Homebridge response: {response.json()}')
	        response.close()
	        print('OK')
	        break

	    except (ValueError, RuntimeError) as e:
	        print('Failed to get data, retrying\n', e)
	        print('Hint: Check IP/access to Homebridge server.')
	        wifi.reset()
	        continue

	response = None
	return

# Wifi Management
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

last_post = time.monotonic()
first_pass = True
switch_1_open = False #Flag to only "0" once if lids are closed
switch_2_open = False #Flag to only "0" once if lids are closed


while True:

    print('--------------------')
    
    now = time.monotonic()

    # Send Batt. terminal information to Adafruit.IO
    if now - last_post >= POST_TIME or first_pass:

        last_post = now

        print("Posting voltage data... ")
        data = get_voltage(vbat_pin)
        print(f'Supply voltage: {data}')

        feed = "supply-voltage"
        post_adafruit(feed, data)
        esp.disconnect()

    # Switch 1
    if switch_1.value: # floating, pulled up = open circuit, door open.
        m4_neopixel[0] = (0, 255, 0)
        switch_1_open = True
        post_adafruit('switch-1', 1)
        post_homebridge('switch-1', 'false')
    else:
        if switch_1_open or first_pass: #prevents constantly sending data to adafruit.io on normal state.

            switch_1_open = False
            m4_neopixel[0] = (0,0,0)
            post_adafruit('switch-1', 0)
            post_homebridge('switch-1', 'true')
            esp.disconnect()


    # Uncomment below to use second switch
    # Note: "switch-2" needs to be setup in the HttpWebHooks section/plugin of the
    # Homebridge configuration file.
    # Switch 2
    #if switch_2.value: # floating, pulled up = open circuit, door open.
    #    m4_neopixel[0] = (0, 0, 255)
    #    switch_2_open = True
    #    post_adafruit('switch-2', 1)
    #    post_homebridge('switch-2', 'false')
    #else:
    #    if switch_2_open or first_pass: #prevents constantly sending data to adafruit.io on normal state.
    #
    #        switch_2_open = False
    #        m4_neopixel[0] = (0,0,0)
    #        post_adafruit('switch-2', 0)
    #        post_homebridge('switch-2', 'true')

    
    first_pass = False 

    time.sleep(3)