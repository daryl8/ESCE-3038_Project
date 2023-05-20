from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
import pytz
import datetime
import pydantic
import requests
from bson import ObjectId
import re
import motor.motor_asyncio
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim



app = FastAPI()

origins = [
    "https://simple-smart-hub-client.netlify.app",
    "https://esce3038-iotproject.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pydantic.json.ENCODERS_BY_TYPE[ObjectId] = str

client = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://IoTproject:iotproject@cluster0.ambk2jl.mongodb.net/")
db = client.iotproject
sensor_data = db['sensor_data']
esp_data = db['data']

# Initialize Nominatim API
geo_locator = Nominatim(user_agent="MyApp")

location = geo_locator.geocode("Hyderabad")


def get_sunset():
    latitude_location =  location.latitude
    longitude_location = location.longitude

    sunset_api_endpoint = f'https://api.sunrise-sunset.org/json?lat={latitude_location}&lng={longitude_location}'

    sunset_api_response = requests.get(sunset_api_endpoint)
    sunset_api_reading = sunset_api_response.json()

    time_of_sunset = datetime.strptime(sunset_api_reading['results']['sunset'], '%I:%M:%S %p').time()
    
    return datetime.strptime(str(time_of_sunset),"%H:%M:%S")


regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')

def parse_time(time_str):
    parts = regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)

@app.get("/")
async def home():
    return {"message": "ECSE3038_Project"}

@app.get('/graph')
async def graph(request: Request):
    size = int(request.query_params.get('size'))
    read_values = await esp_data.find().sort('_id', -1).limit(size).to_list(size)
    reading_data = []
    for things in read_values:
        temperature = things.get("temperature")
        presence = things.get("presence")
        present_time = things.get("present_time")

        reading_data.append({
            "temperature": temperature,
            "presence": presence,
            "datetime": present_time
        })

    return reading_data

@app.put('/settings')
async def get_stored_data(request: Request):
    condition = await request.json()
    
    input_temp = condition["user_temp"]
    light_input = condition["user_light"]
    light_time_off = condition["light_duration"]
    

    if light_input == "sunset":
        light_buffer = get_sunset()
    else:
        light_buffer = datetime.strptime(light_input, "%H:%M:%S")
    
    first_user_light = light_buffer + parse_time(light_time_off)

    output_result = {
        "user_temp": input_temp,
        "user_light": str(light_buffer.time()),
        "light_time_off": str(first_user_light.time())
        }
   
    object = await sensor_data.find().sort('_id', -1).limit(1).to_list(1)

    if object:
        await sensor_data.update_one({"_id": object[0]["_id"]}, {"$set": output_result})
        object_new = await sensor_data.find_one({"_id": object[0]["_id"]})
    else:
        new = await sensor_data.insert_one(output_result)
        object_new = await sensor_data.find_one({"_id": new.inserted_id})
    return object_new


@app.post("/temperature")

async def update(request: Request): 
    condition = await request.json()

    variable = await sensor_data.find().sort('_id', -1).limit(1).to_list(1)
    if variable:
        temperature = variable[0]["user_temp"]   
        input_light = datetime.strptime(variable[0]["user_light"], "%H:%M:%S")
        off_time = datetime.strptime(variable[0]["light_time_off"], "%H:%M:%S")
    else:
        temperature = 28
        input_light = datetime.strptime("18:00:00", "%H:%M:%S")
        off_time = datetime.strptime("20:00:00", "%H:%M:%S")

    now_time = datetime.now(pytz.timezone('Jamaica')).time()
    present_time = datetime.strptime(str(now_time),"%H:%M:%S.%f")


    condition["light"] = ((present_time < input_light) and (present_time < off_time ) & (condition["presence"] == 1))
    condition["fan"] = ((float(condition["temperature"]) >= temperature) & (condition["presence"]== 1))
    condition["current_time"]= str(datetime.now())

    settings_new = await esp_data.insert_one(condition)
    new_obj = await esp_data.find_one({"_id":settings_new.inserted_id}) 
    return new_obj


#retreves last entry
@app.get("/condition")
async def get_state():
    final_entry = await esp_data.find().sort('_id', -1).limit(1).to_list(1)

    if not final_entry:
        return {
            
            "fan": False,
            "light": False,
            "presence": False,
            "current_time": datetime.now()
        }

    return final_entry