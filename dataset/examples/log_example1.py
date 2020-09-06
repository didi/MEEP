# Setup
from utils.utils import load_variable
from apis import GoogleMapsProvider
google_maps_provider = GoogleMapsProvider(
    api_key="<anonymous google maps key>")

print('Agent name: 007')

# Initial variables
source_address = '4640 Admiralty Way, Marina del Rey'
source_latitude = 33.9816425
source_longitude = -118.4409761

# Events

# User utterance
print('User: let\'s go to a coffeeshop')
u1_0 = 'let'
u1_1 = '\'s'
u1_2 = 'go'
u1_3 = 'to'
u1_4 = 'a'
u1_5 = 'coffeeshop'

# API call
api_variables = google_maps_provider.find_place(
    u1_5, source_latitude, source_longitude)
v1_name = load_variable(api_variables, 'name')
v1_address = load_variable(api_variables, 'address')
v1_latitude = load_variable(api_variables, 'latitude')
v1_longitude = load_variable(api_variables, 'longitude')
v1_price_level = load_variable(api_variables, 'price_level')
v1_types_0 = load_variable(api_variables[5]['value'], '0')
v1_types_1 = load_variable(api_variables[5]['value'], '1')
v1_types_2 = load_variable(api_variables[5]['value'], '2')
v1_types_3 = load_variable(api_variables[5]['value'], '3')
v1_types_4 = load_variable(api_variables[5]['value'], '4')
v1_rating = load_variable(api_variables, 'rating')
v1_is_open = load_variable(api_variables, 'is_open')
v1_address_simple = load_variable(api_variables, 'address_simple')
v1_street_number = load_variable(api_variables, 'street_number')
v1_street_name = load_variable(api_variables, 'street_name')
v1_locality = load_variable(api_variables, 'locality')
v1_distance = load_variable(api_variables, 'distance')
v1_duration = load_variable(api_variables, 'duration')
v1_place_id = load_variable(api_variables, 'place_id')

# Agent utterance
print('Agent: There is a {} on {}.'.format(v1_name, v1_street_name))

# User utterance
print('User: Great let\'s go')
u2_0 = 'Great'
u2_1 = 'let'
u2_2 = '\'s'
u2_3 = 'go'

# API call
api_variables = google_maps_provider.start_driving(
    v1_latitude, v1_longitude, v1_place_id)
v2_success = load_variable(api_variables, 'success')
print('Agent ended dialog successfully')
# Correct destination? True
print('Correct destination? True')
