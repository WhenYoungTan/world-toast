import os
import time
import csv
import sqlite3
import random
from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as pd
from flask import Flask, render_template, request
from datetime import datetime
import requests

# To run flask, use python -m flask run on the CLI
app = Flask(__name__)

# Creates a random number that only changes every 24 hours. Taken from https://stackoverflow.com/questions/69396191/generate-a-random-number-which-change-every-24-hours
def daily_random_number():
    d0 = datetime(2008, 8, 18)  # Pick an arbitrary date in the past
    d1 = datetime.now()
    delta = d1 - d0
    random.seed(delta.days)
    return random.randint(1,205)

def format_list(list):
    temp_list = []
    for stuff in list:
        if stuff[0] == None:
            break
        temp_list.append(stuff[0])
    return temp_list

def find_flag(country_code):
    con = sqlite3.connect('world_data.db')
    cur = con.cursor()
    flags = cur.execute("SELECT * FROM flags WHERE Code=\'" + country_code + "'").fetchall()[0]
    con.close()
    return flags[2]

def check_neighbours(country_code):
    con = sqlite3.connect('world_data.db')
    cur = con.cursor()
    country_neighbours = cur.execute("SELECT country.name, flags.Flag_image_url FROM country JOIN country_borders ON country.Code2 = country_borders.country_border_code JOIN flags ON country.Code2 = flags.Code WHERE country_borders.country_code=\'" + country_code + "'").fetchall()
    con.close()
    if len(country_neighbours) == 0:
        return "Your country does not share a land border with any other country"
    else:
        return country_neighbours

def get_news(country_name):
    # APIKEY: 2853be0874c644c294f306f73cb251c2
    # https://newsapi.org/v2/top-headlines?country=sg&apiKey=2853be0874c644c294f306f73cb251c2
    # See https://newsapi.org/docs/get-started#search for documentation

    # Gets current time
    now = datetime.now()

    # Formats URL based on current time and country of choice
    url = ('https://newsapi.org/v2/everything?' +
       'q={}&'.format(country_name) +
       'from={:02d}-{:02d}-{:02d}&'.format(now.year,now.month,now.day) +
       'sortBy=popularity&'
       'apiKey=2853be0874c644c294f306f73cb251c2')
    
    # Gets JSON file
    response = requests.get(url)

    return response.json()

@app.route("/")
def home():
    # Opens database and retrieve country's name
    con = sqlite3.connect('world_data.db')
    cur = con.cursor()
    country_data = cur.execute("SELECT * FROM country WHERE rowid="+str(daily_random_number())).fetchall()[0]
    con.close()

    # Retrieves the flag database for the country of interest using the 2 letter country code.
    flags = find_flag(country_data[14])

    # Webscrape background info of a country from the CIA World Factbook. 
    url = "https://www.cia.gov/the-world-factbook/countries/" + country_data[1].lower().replace(" ","-").replace("(","").replace(")","")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    introduction_html = soup.select('#introduction')
    introduction_text = ""
    for rows in introduction_html:
        introduction_text = rows.find("p").text
        
    # Creates the search string for the embeded google map based on the country var. Search string by https://www.maps.ie/create-google-map/
    country_formated = country_data[1].replace(" ","-")
    embeded_search_string = "https://maps.google.com/maps?width=100%25&height=600&hl=en&q=" + country_formated + "()&t=&&ie=UTF8&iwloc=B&output=embed"

    # Get news info 
    news = get_news(country_data[1])["articles"]
    return render_template("index.html", embeded_search_string=embeded_search_string, country_data=country_data, flags=flags, introduction_text=introduction_text, country_neighbours = format_list(check_neighbours(country_data[14])), news = news)

@app.route("/search")
def search():
    # Formats all country names into a readable list
    con = sqlite3.connect('world_data.db')
    cur = con.cursor()
    all_country_names = format_list(cur.execute("SELECT Name FROM country").fetchall())
    con.close()
    return render_template("search.html", all_country_names=all_country_names)

@app.route("/searched")
def searched():
    # Gets the country query in the search string
    chosen_country = request.args.get("Country")

    # Opens database and retrieve country's data
    con = sqlite3.connect('world_data.db')
    cur = con.cursor()
    country_data = cur.execute("SELECT * FROM country WHERE name=\'" + chosen_country + "'").fetchall()
    con.close()

    # If country not found, returns an error message
    if len(country_data) == 0:
        return render_template("error.html", error_message="ERROR: Unable to find country")
    country_data = country_data[0]

    # Retrieves the flag database for the country of interest using the 2 letter country code.
    flags = find_flag(country_data[14])

    # Webscrape background info of a country from the CIA World Factbook. 
    url = "https://www.cia.gov/the-world-factbook/countries/" + country_data[1].lower().replace(" ","-").replace("(","").replace(")","")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    introduction_html = soup.select('#introduction')
    introduction_text = ""
    for rows in introduction_html:
        introduction_text = rows.find("p").text
        
    # Creates the search string for the embeded google map based on the country var. Search string by https://www.maps.ie/create-google-map/
    country_formated = country_data[1].replace(" ","-")
    embeded_search_string = "https://maps.google.com/maps?width=100%25&height=600&hl=en&q=" + country_formated + "()&t=&&ie=UTF8&iwloc=B&output=embed" 
    
    # Get news info 
    news = get_news(country_data[1])["articles"]
    return render_template("index.html", embeded_search_string=embeded_search_string, country_data=country_data, flags=flags, introduction_text=introduction_text, country_neighbours = format_list(check_neighbours(country_data[14])), news = news)
@app.route("/see-neighbours")
def see_neighbours():
    # Check ip address of user  
    response_ip = requests.get('https://api64.ipify.org?format=json').json()
    ip_addr = response_ip["ip"]

    # Checks country code of ip address
    response = requests.get(f'https://ipapi.co/{ip_addr}/json/?key=uvPfKJqjxi5JxZbcsep08XXJrweVIFVcnRIraSIxqQXwYUtbXZ').json()
    country_code = response.get("country_code")
    country_name = response.get("country_name")

    # Returns error message if api key fails
    if response.get("error") == True:
        return render_template("error.html", error_message="ERROR: Unable to determine your location")

    # Retrieves data about user's country neighbours
    return render_template("see_neighbours.html", country_name=country_name, flags = find_flag(country_code), country_neighbours=check_neighbours(country_code))

# Basic country data from https://dev.mysql.com/doc/index-other.html
# flag url database from https://data.world/g-delgado-g/country-flags-and-country-codes-iso-3166-2/workspace/file?filename=Countries_code_flags.csv