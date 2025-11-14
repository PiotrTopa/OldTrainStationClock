from machine import Pin, RTC
import time
from collections import namedtuple

TIME_SERVICE_URL = 'http://worldtimeapi.org/api/timezone/CET'

TimeValue = namedtuple("TimeValue", ("hours", "minutes", "seconds"))

class Clock:
    current_display_minutes = 0
    
    
    def __init__(self, nenabled_pin_number:int, step_pin_number: int, led_pin_number: int, configuration_filename: str = "configuration.json", display_time: str = None) -> None:
        self.configuration_filename = configuration_filename
        if display_time is not None:
            display_timevalue = self.parse_time_string(display_time)
            self.current_display_minutes = self.calculate_display_minutes(display_timevalue)
            self.store_configuration()
        else:
            self.load_configuration()
        
        self.rtc = RTC()
        self.pin_step = Pin(step_pin_number, Pin.OUT)
        self.pin_nenabled = Pin(nenabled_pin_number, Pin.OUT)
        self.pin_nenabled.on()
        self.pin_led = Pin(led_pin_number, Pin.OUT)
        self.pin_led.on()
        
            
    def sync_rtc_online(self):
        import requests
        from machine import RTC
        self.pin_led.on()
        try:
            print('Online time synchronization started...')    
            response = requests.get(TIME_SERVICE_URL)
            data = response.json()
            print('Received response: ', str(data))
            parse1 = data["datetime"]
            parse2 = parse1.replace("-",".").replace("+",":").replace("T",":").replace(".", ":")
            parse3 = parse2.split(":")
            year = int(parse3[0])
            month = int(parse3[1])
            day = int(parse3[2])
            hour = int(parse3[3])
            minute = int(parse3[4])
            second = int(parse3[5])
            microsecond = int(parse3[6])
            day_of_week = int(data['day_of_week'] - 1)
            datetime_tuple = (year, month, day, day_of_week, hour, minute, second, microsecond)
            self.rtc.datetime(datetime_tuple)
            print('Time synchronization success.')
            self.pin_led.off()
        except Exception:
            print('Time synchronization fail.')
        

    def store_configuration(self):
        import json
        configuration = {
            "display": self.current_display_minutes   
        }
        file = open(self.configuration_filename, "w")
        file.write(json.dumps(configuration))


    def load_configuration(self):
        import json
        file = open(self.configuration_filename, "r")
        configuration = json.loads(file.read())
        print('Configuration loaded', str(configuration))
        self.current_display_minutes = configuration["display"]
        
        
    def calculate_display_minutes(self, time: TimeValue):
        return ((time.hours * 60) + time.minutes) % (12 * 60)


    def parse_time_string(self, value: str) -> TimeValue:
        splitted = value.split(":")
        if(len(splitted) < 2 or len(splitted) > 3):
            raise Exception("Invalida time format")
        hours = int(splitted[0])
        minutes = int(splitted[1])
        seconds = 0
        if(len(splitted) == 3):
            seconds = int(splitted[2])
        return TimeValue(hours=hours, minutes=minutes, seconds=seconds)
    
    
    def tick(self):
        self.pin_nenabled.off()
        time.sleep_ms(10)
        for i in range(0, 2):
            self.pin_step.on()
            time.sleep_ms(25)
            self.pin_step.off()
            time.sleep_ms(250)
        self.pin_nenabled.on()
        self.current_display_minutes = (self.current_display_minutes + 1) % (12 * 60)
        self.store_configuration()
        
        
    def set_display_time(self, target_display_value: TimeValue):
        target_display_minutes = self.calculate_display_minutes(target_display_value)
        while(self.current_display_minutes != target_display_minutes):
            self.tick()
            print(str(self.current_display_minutes) + "->" + str(target_display_minutes))
             
    
    def start(self):
        last_sync_hour = None
        while(True):
            ctime = self.rtc.datetime()
            print(ctime)
            current_timevalue = TimeValue(hours=ctime[4], minutes=ctime[5], seconds=ctime[6])
            if current_timevalue.hours != last_sync_hour:
                self.sync_rtc_online()
                last_sync_hour = current_timevalue.hours
            self.set_display_time(current_timevalue)
            ctime = self.rtc.datetime()
            delta = 60 - ctime[6]
            time.sleep(delta)
        
