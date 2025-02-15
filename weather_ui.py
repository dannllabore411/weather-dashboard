import calendar, pytz
from datetime import date, datetime, timezone
import openmeteo_requests
from geopy.geocoders import Nominatim
import streamlit as st
import requests_cache
import pandas as pd
from retry_requests import retry
import folium
import plotly.express as px
# Initializing OpenMeteo session
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)
# Sidebar Input
title = "Weather Dashboard"
st.set_page_config(layout="wide", page_icon="🌡️", page_title=title)
with st.sidebar:
    city = st.text_input("Input city:", placeholder="General Santos")
# Preparing location with Geopy geocoder Nominatim
geolocator = Nominatim(user_agent="weather_test")
location = geolocator.geocode(city)
latitude = location.latitude
longitude = location.longitude
# Make sure all required weather variables are listed here, the order of variables in hourly or daily is important to assign them correctly below
url = "https://api.open-meteo.com/v1/forecast"
params = {
	"latitude": latitude,
	"longitude": longitude,
	"current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation", "cloud_cover", "surface_pressure", "wind_speed_10m", "wind_direction_10m"],
	"hourly": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation_probability", "precipitation", "surface_pressure", "cloud_cover"],
	"timezone": "auto"
}
responses = openmeteo.weather_api(url, params=params)
# Process first location.
response = responses[0]
timezone = response.Timezone().decode('utf-8')
now = datetime.now(pytz.timezone(timezone))
# Current values. The order of variables needs to be the same as requested.
current = response.Current()
current_temperature_2m = current.Variables(0).Value()
current_relative_humidity_2m = current.Variables(1).Value()
current_apparent_temperature = current.Variables(2).Value()
current_precipitation = current.Variables(3).Value()
current_cloud_cover = current.Variables(4).Value()
current_surface_pressure = current.Variables(5).Value()
current_wind_speed_10m = current.Variables(6).Value()
current_wind_direction_10m = current.Variables(7).Value()
# Hourly data. The order of variables needs to be the same as requested.
hourly = response.Hourly()
hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
hourly_apparent_temperature = hourly.Variables(2).ValuesAsNumpy()
hourly_precipitation_probability = hourly.Variables(3).ValuesAsNumpy()
hourly_precipitation = hourly.Variables(4).ValuesAsNumpy()
hourly_surface_pressure = hourly.Variables(5).ValuesAsNumpy()
hourly_cloud_cover = hourly.Variables(6).ValuesAsNumpy()
hourly_data = {"Time": pd.date_range(
	start = pd.to_datetime(hourly.Time(), unit = "s", utc = True).tz_convert(timezone),
	end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True).tz_convert(timezone),
	freq = pd.Timedelta(seconds = hourly.Interval()),
	inclusive = "left"
)}
hourly_data["Temperature"] = hourly_temperature_2m
hourly_data["Relative Humidity"] = hourly_relative_humidity_2m
hourly_data["Apparent Temperature"] = hourly_apparent_temperature
hourly_data["Precipitation Probability"] = hourly_precipitation_probability
hourly_data["Precipitation"] = hourly_precipitation
hourly_data["Surface Pressure"] = hourly_surface_pressure
hourly_data["Cloud Cover"] = hourly_cloud_cover
hourly_dataframe = pd.DataFrame(data = hourly_data)
hfdf = hourly_dataframe.copy()
# UI - Title, Col_Top = Weather
st.title(f"{location.raw["name"]}")
col_top = st.columns((1,3), gap="small", border=True)
with col_top[0]:
	st.markdown(f"## {current_temperature_2m:.0f}°C")
	st.markdown(f"Feels like {current_apparent_temperature:.0f}°C<br>{current_cloud_cover:.0f}% cloudy, {current_relative_humidity_2m:.0f}% RH<br><b>{now.time().strftime("%I:%M %p")} ({response.TimezoneAbbreviation().decode()})</b>", 
			 unsafe_allow_html=True)
with col_top[1]:
	hfdf["Date"] = hfdf["Time"].dt.date.copy()
	result = hfdf.groupby("Date").agg({"Temperature": ["mean", "max", "min"], "Precipitation Probability": "mean"})
	col_days = st.columns(5, gap="small")
	with col_days[0]:
		st.markdown(f"## {result.iloc[0,0]:.0f}°C")
		st.markdown(f"Today<br>{result.iloc[0,1]:.0f}°C/{result.iloc[0,2]:.0f}°C<br>{result.iloc[0,3]:.0f}% rain", 
			  unsafe_allow_html=True)
	with col_days[1]:
		st.markdown(f"## {result.iloc[1,0]:.0f}°C")
		st.markdown(f"Tomorrow<br>{result.iloc[1,1]:.0f}°C/{result.iloc[1,2]:.0f}°C<br>{result.iloc[1,3]:.0f}% rain", 
			  unsafe_allow_html=True)
	with col_days[2]:
		st.markdown(f"## {result.iloc[2,0]:.0f}°C")
		st.markdown(f"{calendar.day_name[hfdf["Time"].iloc[2].weekday()]}<br>{result.iloc[2,1]:.0f}°C/{result.iloc[2,2]:.0f}°C<br>{result.iloc[2,3]:.0f}% rain", 
			  unsafe_allow_html=True)
	with col_days[3]:
		st.markdown(f"## {result.iloc[3,0]:.0f}°C")
		st.markdown(f"{calendar.day_name[hfdf["Time"].iloc[3].weekday()]}<br>{result.iloc[3,1]:.0f}°C/{result.iloc[3,2]:.0f}°C<br>{result.iloc[3,3]:.0f}% rain", 
			  unsafe_allow_html=True)
	with col_days[4]:
		st.markdown(f"## {result.iloc[4,0]:.0f}°C")
		st.markdown(f"{calendar.day_name[hfdf["Time"].iloc[4].weekday()]}<br>{result.iloc[4,1]:.0f}°C/{result.iloc[4,2]:.0f}°C<br>{result.iloc[4,3]:.0f}% rain", 
			  unsafe_allow_html=True)
# UI - Col_Bot = Graphs and Map
col_bot = st.columns((2,2), gap="small", border=True)
with col_bot[0]:
	h_data = hfdf[hfdf["Time"] > now].copy()
	h_data["Time"] = pd.to_datetime(h_data["Time"]).dt.strftime("%I%p")
	h_data = h_data.head(24).reset_index()
	h_data = h_data.drop(["index", "Date"], axis=1)
	h_data = h_data.set_index("Time")
	var_list = h_data.columns.values.tolist()
	variable = st.selectbox(label="Select variable to show 24-hour trend:", options=var_list)
	figure = px.scatter(h_data, x=h_data.index, y=variable, title=f"24-Hour {variable} Forecast for {city}", height=300)
	st.plotly_chart(figure)
with col_bot[1]:
	map1 = folium.Map(location=[response.Latitude(), response.Longitude()], zoom_start=7, tiles="Stadia.Outdoors")
	st.components.v1.html(folium.Figure().add_child(map1).render())
	st.write(f"Coordinates {response.Latitude():.2f}°N {response.Longitude():.2f}°E, Elevation {response.Elevation():.0f} m asl")
	st.write(f"Precipitation {current_precipitation:.2f} mm")
	st.write(f"Surface Pressure {current_surface_pressure:.0f} hPa")
	st.write(f"Wind Speed {current_wind_speed_10m:.1f} km/h")