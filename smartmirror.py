# smartmirror.py
# requirements
# requests, feedparser, traceback, Pillow

from tkinter import *
import locale
import threading
import time
import requests
import json
import traceback
import feedparser
import numpy as np
import os

from PIL import Image, ImageTk
from contextlib import contextmanager

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from GoogleWeather.GoogleWeather import GoogleWeatherAPI
from SurflineScraper.SurflineScraper import SurflineScraper
from iWindsurfScraper.iWindsurfScraper import iWindsurfScraper

LOCALE_LOCK = threading.Lock()

ui_locale = '' # e.g. 'fr_FR' fro French, '' as default
time_format = 12 # 12 or 24
date_format = "%b %d, %Y" # check python doc for strftime() for options
news_country_code = 'us'
weather_region = 'Redwood City'
surf_region = 'OCEAN_BEACH_OVERVIEW'
# wind_locations = ['3Rd AVE CHANNEL', 'Anita Rock-Crissy Field', 'Palo Alto', 'Coyote Point']
wind_locations = ['3RD AVE CHANNEL']
xlarge_text_size = 50
large_text_size = 48
medium_text_size = 28
small_text_size = 12

# FRAME_DEBUG = {'highlightbackground': "white",
#                'highlightthickness': 1}

FRAME_DEBUG = {'highlightbackground': None,
               'highlightthickness': 0}


@contextmanager
def setlocale(name): #thread proof function to work with locale
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)

# maps open weather icons to
# icon reading is not impacted by the 'lang' parameter
icon_lookup = {
    'Clear': "assets/Sun.png",  # clear sky day
    'wind': "assets/Wind.png",   #wind
    'cloudy': "assets/Cloud.png",  # cloudy day
    'partly-cloudy-day': "assets/PartlySunny.png",  # partly cloudy day
    'rain': "assets/Rain.png",  # rain day
    'snow': "assets/Snow.png",  # snow day
    'snow-thin': "assets/Snow.png",  # sleet day
    'fog': "assets/Haze.png",  # fog day
    'clear-night': "assets/Moon.png",  # clear sky night
    'partly-cloudy-night': "assets/PartlyMoon.png",  # scattered clouds night
    'thunderstorm': "assets/Storm.png",  # thunderstorm
    'tornado': "assests/Tornado.png",    # tornado
    'hail': "assests/Hail.png"  # hail
}


class Clock(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')

        # initialize time label
        self.time1 = ''
        self.timeLbl = Label(self, font=('Helvetica', large_text_size), fg="white", bg="black", **FRAME_DEBUG)
        self.timeLbl.pack(side=TOP, anchor=E)

        # initialize day of week
        self.day_of_week1 = ''
        self.dayOWLbl = Label(self, text=self.day_of_week1, font=('Helvetica', small_text_size), fg="white", bg="black", **FRAME_DEBUG)
        self.dayOWLbl.pack(side=TOP, anchor=E)

        # initialize date label
        self.date1 = ''
        self.dateLbl = Label(self, text=self.date1, font=('Helvetica', small_text_size), fg="white", bg="black", **FRAME_DEBUG)
        self.dateLbl.pack(side=TOP, anchor=E)
        self.tick()

    def tick(self):
        with setlocale(ui_locale):
            if time_format == 12:
                time2 = time.strftime('%I:%M %p') #hour in 12h format
            else:
                time2 = time.strftime('%H:%M') #hour in 24h format

            day_of_week2 = time.strftime('%A')
            date2 = time.strftime(date_format)
            # if time string has changed, update it
            if time2 != self.time1:
                self.time1 = time2
                self.timeLbl.config(text=time2)
            if day_of_week2 != self.day_of_week1:
                self.day_of_week1 = day_of_week2
                self.dayOWLbl.config(text=day_of_week2)
            if date2 != self.date1:
                self.date1 = date2
                self.dateLbl.config(text=date2)
            # calls itself every 200 milliseconds
            # to update the time display as needed
            # could use >200 ms, but display gets jerky
            self.timeLbl.after(1000, self.tick)


class Surf(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black', **FRAME_DEBUG)
        self.surfline = SurflineScraper()
        self.temperature = ''
        self.icon = ''
        
        # Initialize variables to later be updated
        self.dummy_x = None
        self.x_ticks = None
        self.ax = None
        self.canvas = None
        self.fig = None
        
        # Plot future Data
        self.plot_frame = Frame(self, bg="black", **FRAME_DEBUG)
        self.plot_frame.pack(side=TOP, anchor=W)
        self.surf_data = None
        self.MakeForecastPlot()
    
    def MakeForecastPlot(self):
        print('Making Surf Forecast')
        first_time = self.canvas is None
                
        surf_data = self.surfline.GetData(surf_region)
        
        if not first_time:
            if np.average(surf_data['Wave Avg Height [ft]'].values) == np.average(self.surf_data['Wave Avg Height [ft]'].values):
                self.after(10000, self.MakeForecastPlot)
                return
        
        self.surf_data = surf_data
        
        if first_time:
            self.fig = plt.figure(figsize=(5, 3), facecolor='black')
        else:
            self.fig.gca().clear()

        plt.figure(self.fig.number)
        self.surfline.PlotSurfResults(surf_region)
        
        self.ax = self.fig.gca()
        ax = self.ax
        ax.patch.set_facecolor('black')

        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        
        if first_time:
            plt.tight_layout()
            self.canvas = FigureCanvasTkAgg(self.fig, self.plot_frame)
            self.canvas.get_tk_widget().pack(side=BOTTOM, fill=BOTH,
                                             expand=True)
        
        self.canvas.draw()
        self.after(200000, self.MakeForecastPlot)


class Wind(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black', **FRAME_DEBUG)
        self.iwindsurf = iWindsurfScraper()
        self.temperature = ''
        self.icon = ''
        
        # Initialize variables to later be updated
        self.dummy_x = None
        self.x_ticks = None
        self.ax = None
        self.canvas = None
        self.fig = None
        
        # Plot future Data
        self.plot_frame = Frame(self, bg="black", **FRAME_DEBUG)
        self.plot_frame.pack(side=TOP, anchor=W)
        self.wind_data = None
        self.wind_loc_index = 0
        self.MakeForecastPlot()
    
    def MakeForecastPlot(self):
        print('Making WindSurf Forecast')
        first_time = self.canvas is None
        location_idx = self.wind_loc_index
        location = wind_locations[location_idx]
        wind_data = self.iwindsurf.GetData(location)
        
        if not first_time:
            if np.average(wind_data['Wind Speed [mph]'].values) == np.average(self.wind_data['Wind Speed [mph]'].values):
                self.after(10000, self.MakeForecastPlot)
                return

        self.wind_data = wind_data
        
        if first_time:
            self.fig = plt.figure(figsize=(5, 3), facecolor='black')
        else:
            self.fig.gca().clear()

        plt.figure(self.fig.number)
        self.iwindsurf.PlotWindForecast(location)
        
        self.ax = self.fig.gca()
        ax = self.ax
        ax.patch.set_facecolor('black')

        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')    
        
        if first_time:
            plt.tight_layout()
            self.canvas = FigureCanvasTkAgg(self.fig, self.plot_frame)
            self.canvas.get_tk_widget().pack(side=BOTTOM, fill=BOTH,
                                             expand=True)
        
        self.canvas.draw()
        self.wind_loc_index = np.remainder(self.wind_loc_index + 1, len(wind_locations))
        self.after(200000, self.MakeForecastPlot)


class Weather(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black', **FRAME_DEBUG)
        self.google_weather = GoogleWeatherAPI()
        self.temperature = ''
        self.forecast = ''
        self.location = ''
        self.currently = ''
        self.icon = ''
        
        # Initialize variables to later be updated
        self.weather_data = None
        self.dummy_x = None
        self.x_ticks = None
        self.ax = None
        self.canvas = None
        self.fig = None

        # Weather debug
        # self.weather_data = np.array([10, 10, 11, 11, 12, 9, 8, 8])
        # self.weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
        #                  'Saturday', 'Sunday', 'Monday']

        self.temperatureLbl = Label(self, font=('Helvetica', xlarge_text_size), fg="white", bg="black", **FRAME_DEBUG)
        self.temperatureLbl.pack(side=TOP, anchor=W)

        self.degreeFrm = Frame(self, bg="black", **FRAME_DEBUG)
        self.degreeFrm.pack(side=TOP, anchor=W)
        
        self.currentlyLbl = Label(self.degreeFrm, font=('Helvetica', medium_text_size), fg="white", bg="black", **FRAME_DEBUG)
        self.currentlyLbl.pack(side=LEFT, anchor=N)
        
        self.iconLbl = Label(self.degreeFrm, bg="black", **FRAME_DEBUG)
        self.iconLbl.pack(side=TOP, anchor=W, padx=10)

        self.forecastLbl = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black", **FRAME_DEBUG)
        self.forecastLbl.pack(side=TOP, anchor=W)
        
        self.locationLbl = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black", **FRAME_DEBUG)
        self.locationLbl.pack(side=TOP, anchor=W)
        self.get_weather()

        # Plot future Data
        self.plot_frame = Frame(self, bg="black", **FRAME_DEBUG)
        self.plot_frame.pack(side=TOP, anchor=W)
        self.MakeForecastPlot()

    def MakeForecastPlot(self):
        
        first_time = self.canvas is None
    
        self.dummy_x = np.arange(0, 8, 1)

        weather_data = self.google_weather.GetDataFromRegion(weather_region)
        # weather_data = np.append(self.weather_data[1:], self.weather_data[0])
        # self.weekdays = self.weekdays[1:] + [self.weekdays[0]]
        if not (weather_data == self.weather_data):
        # if True:
    
            self.weather_data = weather_data
        
            min_temp = []
            max_temp = []
            ave_temp = []
            weekdays = []
            for dayweather in weather_data['next_days']:
                min_temp += [dayweather['min_temp_c']]
                max_temp += [dayweather['max_temp_c']]
                ave_temp += [(max_temp[-1] + min_temp[-1]) / 2]
                weekdays += [dayweather['name']]
            
            # for idx, num in enumerate(self.weather_data):
            #     min_temp += [num-1]
            #     max_temp += [num+1]
            #     ave_temp += [num]
            #     weekdays += [self.weekdays[idx]]
            
            if first_time:
                self.fig = plt.figure(figsize=(5, 3), facecolor='black')
            else:
                self.fig.gca().clear()

            plt.figure(self.fig.number)
    
            plt.plot(self.dummy_x, max_temp, linewidth=1, markersize=6, color='white', markeredgecolor='white', linestyle='--')
            plt.plot(self.dummy_x, ave_temp, linewidth=2, markersize=6, color='white', markeredgecolor='white')
            plt.plot(self.dummy_x, min_temp, linewidth=1, markersize=6, color='white', markeredgecolor='white', linestyle='--')
            
            self.ax = self.fig.gca()
            ax = self.ax
            ax.patch.set_facecolor('black')
            
            # Set ticks and tick labels
            y_ticks = np.arange(np.min(min_temp), np.max(max_temp), 5)
            plt.xticks(self.dummy_x, weekdays, rotation=45)
            plt.yticks(y_ticks, y_ticks)
            
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            
            if first_time:
                plt.title('Temperature Forecast [degC]', color='white', fontsize=12)
                plt.tight_layout()
                self.canvas = FigureCanvasTkAgg(self.fig, self.plot_frame)
                self.canvas.get_tk_widget().pack(side=BOTTOM, fill=BOTH, expand=True)
              
            self.canvas.draw()
        
        self.after(200000, self.MakeForecastPlot)

    def get_weather(self):
        try:

            weather_data = self.google_weather.GetDataFromRegion(weather_region)

            degree_sign = u'\N{DEGREE SIGN}'
            temperature_c = weather_data['temp_c']
            currently2 = weather_data['weather_now'].title()
            forecast2 = None

            icon2 = icon_lookup[currently2] if currently2 in icon_lookup else None

            if icon2 is not None:
                if self.icon != icon2:
                    self.icon = icon2
                    image = Image.open(icon2)
                    image = image.resize((30, 30), Image.ANTIALIAS)
                    image = image.convert('RGB')
                    photo = ImageTk.PhotoImage(image)

                    self.iconLbl.config(image=photo)
                    self.iconLbl.image = photo
            else:
                # remove image
                self.iconLbl.config(image='')

            if self.currently != currently2:
                self.currently = currently2
                self.currentlyLbl.config(text=currently2)
            if self.forecast != forecast2:
                self.forecast = forecast2
                self.forecastLbl.config(text=forecast2)
            if self.temperature != temperature_c:
                self.temperature = temperature_c
                temperature_f = self.google_weather.CelsiusToFarenheit(temperature_c)
                temperature_string = '%i°C / %i°F' % (temperature_c, temperature_f)
                self.temperatureLbl.config(text=temperature_string)
            if self.location != weather_region:
                if weather_region == ", ":
                    self.location = "Cannot Pinpoint Location"
                    self.locationLbl.config(text="Cannot Pinpoint Location")
                else:
                    self.location = weather_region
                    self.locationLbl.config(text=weather_region)
        except Exception as e:
            traceback.print_exc()
            print("Error: %s. Cannot get weather." % e)

        self.after(600000, self.get_weather)


class News(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.config(bg='black')
        self.title = 'News'  # 'News' is more internationally generic
        self.newsLbl = Label(self, text=self.title, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.newsLbl.pack(side=TOP, anchor=W)
        self.headlinesContainer = Frame(self, bg="black")
        self.headlinesContainer.pack(side=TOP)
        self.get_headlines()

    def get_headlines(self):
        try:
            # remove all children
            for widget in self.headlinesContainer.winfo_children():
                widget.destroy()
            if news_country_code == None:
                headlines_url = "https://news.google.com/news?ned=us&output=rss"
            else:
                headlines_url = "https://news.google.com/news?ned=%s&output=rss" % news_country_code

            feed = feedparser.parse(headlines_url)

            for post in feed.entries[0:5]:
                headline = NewsHeadline(self.headlinesContainer, post.title)
                headline.pack(side=TOP, anchor=W)
        except Exception as e:
            traceback.print_exc()
            print("Error: %s. Cannot get news.") % e

        self.after(600000, self.get_headlines)


class NewsHeadline(Frame):
    def __init__(self, parent, event_name=""):
        Frame.__init__(self, parent, bg='black')

        image = Image.open("assets/Newspaper.png")
        image = image.resize((25, 25), Image.ANTIALIAS)
        image = image.convert('RGB')
        photo = ImageTk.PhotoImage(image)

        self.iconLbl = Label(self, bg='black', image=photo)
        self.iconLbl.image = photo
        self.iconLbl.pack(side=LEFT, anchor=N)

        self.eventName = event_name
        self.eventNameLbl = Label(self, text=self.eventName, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.eventNameLbl.pack(side=LEFT, anchor=N)


class Calendar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        self.title = 'Calendar Events'
        self.calendarLbl = Label(self, text=self.title, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.calendarLbl.pack(side=TOP, anchor=E)
        self.calendarEventContainer = Frame(self, bg='black')
        self.calendarEventContainer.pack(side=TOP, anchor=E)
        self.get_events()

    def get_events(self):
        #TODO: implement this method
        # reference https://developers.google.com/google-apps/calendar/quickstart/python

        # remove all children
        for widget in self.calendarEventContainer.winfo_children():
            widget.destroy()

        calendar_event = CalendarEvent(self.calendarEventContainer)
        calendar_event.pack(side=TOP, anchor=E)
        pass


class CalendarEvent(Frame):
    def __init__(self, parent, event_name="Event 1"):
        Frame.__init__(self, parent, bg='black')
        self.eventName = event_name
        self.eventNameLbl = Label(self, text=self.eventName, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.eventNameLbl.pack(side=TOP, anchor=E)


class FullscreenWindow:

    def __init__(self):
        self.tk = Tk()
        self.tk.configure(background='black')
        self.topFrame = Frame(self.tk, background='black', **FRAME_DEBUG)
        self.topLeftFrame = Frame(self.topFrame, background='black', **FRAME_DEBUG)
        self.bottomFrame = Frame(self.tk, background='black', **FRAME_DEBUG)
        self.topFrame.pack(side=TOP, fill=BOTH, expand=YES)
        self.topLeftFrame.pack(side=LEFT, fill=BOTH, expand=YES)
        self.bottomFrame.pack(side=BOTTOM, fill=BOTH, expand=YES)
        self.state = False

        # Set keys to maximize or minimize window
        self.tk.bind("<Return>", self.toggle_fullscreen)
        self.tk.bind("<Escape>", self.end_fullscreen)

        # clock
        self.clock = Clock(self.topFrame)
        self.clock.pack(side=RIGHT, anchor=N, padx=10, pady=20)

        # # weather
        self.weather = Weather(self.topLeftFrame)
        self.weather.pack(side=TOP, anchor=W, padx=10, pady=20)

        # surf
        self.surf = Surf(self.topLeftFrame)
        self.surf.pack(side=TOP, anchor=W, padx=10, pady=0)

        # wind
        self.wind = Wind(self.topLeftFrame)
        self.wind.pack(side=TOP, anchor=W, padx=10, pady=0)

        # news
        self.news = News(self.bottomFrame)
        self.news.pack(side=LEFT, anchor=S, padx=100, pady=60)
        # calender - removing for now
        # self.calender = Calendar(self.bottomFrame)
        # self.calender.pack(side = RIGHT, anchor=S, padx=100, pady=60)

    def toggle_fullscreen(self, event=None):
        self.state = not self.state  # Just toggling the boolean
        self.tk.attributes("-fullscreen", self.state)
        return "break"

    def end_fullscreen(self, event=None):
        self.state = False
        self.tk.attributes("-fullscreen", False)
        return "break"


if __name__ == '__main__':

    if os.environ.get('DISPLAY', '') == '':
        print('no display found. Using :0.0')
        os.environ.__setitem__('DISPLAY', ':0.0')

    w = FullscreenWindow()
    w.tk.mainloop()
