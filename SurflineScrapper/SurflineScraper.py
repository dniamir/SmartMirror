"""Simple class to read surfline data and return as a dataframe:

While the swell data is available on an hourly basis, this code simply returns
the min, max, and average waves over four 6 hour periods of the day

The data itself isn't stored on the Surfline website.  When the website is
loaded, a call to an external API is made. This class reads the external page.

This includes data that is behind the Surfline paywall.

Currently there's no functionality to change the number of datapoints returned
or other options. However if you modify the URL link, this is fairly easy.

"""
from bs4 import BeautifulSoup as bs
import json
import numpy as np
import matplotlib.pyplot as plt
import datetime
import pandas as pd
import requests


class SurflineScraper(object):
	"""Simple class to record and save data from Surfline

	Data is saved as a class variable. The highest level in this dictionary is the
	region name. The next level down is also a dictionary with all recently saved
	data"""
	USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
	LANGUAGE = "en-US,en;q=0.5"
	URL = "https://services.surfline.com/kbyg/spots/forecasts/wave?spotId=_ENTER_SPOT_ID_HERE_&days=6&intervalHours=1&maxHeights=false&sds=false"
	DOTW = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
	        'Sunday']
	
	LOCATION_LOOKUP = {'PACIFICA_LINDA_MAR': '5842041f4e65fad6a7708976',
	                   'PACIFICA_LINDAMAR': '5842041f4e65fad6a7708976',
	                   'OCEAN_BEACH_OVERVIEW': '5842041f4e65fad6a77087f8'}
	
	def __init__(self):
		self.data = {}

	def GetData(self, location):
		"""Read the online Surfline data and return data as a dataframe

		Args:
			location: String. Either the Surfline location code associated with the
				location of interest, of the location name itself as long as it's been
				pre-recorded in the class location lookup dictionary.

		Outputs:
			df_surf: DataFrame. Dataframe with wave height and timestamps.
		"""
		if location.upper() in list(self.LOCATION_LOOKUP):
			location = self.LOCATION_LOOKUP[location.upper()]
		
		url_location = self.URL
		url_location = url_location.replace('_ENTER_SPOT_ID_HERE_', location, 1)
		
		# Read data from URL
		session = requests.Session()
		session.headers['User-Agent'] = self.USER_AGENT
		session.headers['Accept-Language'] = self.LANGUAGE
		session.headers['Content-Language'] = self.LANGUAGE
		html = session.get(url_location)
		soup = bs(html.text, "html.parser")
		soup_text = soup.text
		surf_dict = json.loads(soup_text)
		
		df_surf = self.SimplifyData(surf_dict)
		self.data[location] = df_surf
		
		return df_surf
		
	def SimplifyData(self, surf_dict):
		"""Read in json file information from the Surfline website and parse it

		Args:
			surf_dict: Dictionary. Dictonary format of the json read from the Surfline
				website with data

		Outputs:
			df: DataFrame. Dataframe with wave height and timestamps.
		"""
		waves = surf_dict['data']['wave']

		wave_heights_max = []
		wave_heights_min = []
		wave_heights_avg = []
		wave_timestamp = []
		dotws = []
		
		for wave in waves[::6]:
			min_wave = wave['surf']['min']
			max_wave = wave['surf']['max']
			
			wave_heights_max += [max_wave]
			wave_heights_min += [min_wave]
			
			mean_wave_height = np.mean([min_wave, max_wave])
			wave_heights_avg += [mean_wave_height]
			
			wave_timestamp += [wave['timestamp']]
			dotws += [self.DOTW[datetime.datetime.fromtimestamp(wave_timestamp[-1]).weekday()]]
		
		df = pd.DataFrame({'Timestamp': wave_timestamp,
		                   'Weekday': dotws,
		                   'Wave Max Height [ft]': wave_heights_max,
		                   'Wave Min Height [ft]': wave_heights_min,
		                   'Wave Avg Height [ft]': wave_heights_avg,
		                   })
		
		return df
	
	def PlotSurfResults(self, location):
		"""Plot the surf data in bar chart format
		
		Currently works only if 6 days worth of data is presentd with 4 datapoints
		per day. Will eventually make this function work with more custom data.

		Args:
			location: String. Either the Surfline location code associated with the
				location of interest, of the location name itself as long as it's been
				pre-recorded in the class location lookup dictionary.
		"""
		if location.upper() in list(self.LOCATION_LOOKUP):
			location_key = self.LOCATION_LOOKUP[location.upper()]
		
		df_surf = self.data[location_key]
		
		days = 6
		points_per_day = 4
		
		weekdays = df_surf['Weekday'].values
		wave_max_height = df_surf['Wave Max Height [ft]'].values
		wave_avg_height = df_surf['Wave Avg Height [ft]'].values
		
		diff = wave_max_height - wave_avg_height
		
		x = np.arange(0, len(weekdays), 1)
		x_labels = ['12AM', '6AM', '12PM', '6PM'] * days
		
		for i in range(days):
			x_data = x[i * points_per_day:(i + 1) * points_per_day]
			y_data = wave_avg_height[i * points_per_day:(i + 1) * points_per_day]
			diff_data = diff[i * points_per_day:(i + 1) * points_per_day]
			
			rects = plt.bar(x=x_data, height=y_data, width=1,
			                edgecolor='black')
			
			# Draw red vertical lines
			# if i != days - 1:
			# 	plt.axvline(x_data[-1] + 0.5, color='red', markersize=0, linestyle='--',
			# 	            linewidth=3)
			
			# # Annotate Bars
			# for rect in rects:
			# 	height = rect.get_height()
			# 	plt.gca().annotate('%.1f' % height,
			# 	                   xy=(rect.get_x() + rect.get_width() / 2, height + 1),
			# 	                   xytext=(0, 3),  # 3 points vertical offset
			# 	                   textcoords="offset points",
			# 	                   ha='center', va='bottom', fontsize=12, color='white')
			#
			# # Add Weekday Labels
			# plt.gca().text(x=np.mean(x_data) - 1, y=np.max(wave_max_height) + 1.5,
			#                s=weekdays[i], fontsize=20, color='white')
		
		plt.gca().yaxis.grid(True)
		_ = plt.xticks(ticks=x[::2], labels=x_labels[::2], rotation=30, fontsize=10)
		# plt.xlabel('Time [HR]', fontsize=18)
		# plt.ylabel('Wave Size [ft]', fontsize=18)
		plt.title('%s Surf Report [Ft]' % location.replace('_', ' ').title(), fontsize=12, color='white')
	