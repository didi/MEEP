from collections import namedtuple, defaultdict, Counter
import dbm
from datetime import datetime, timedelta
import json

from wit import Wit
from darksky import forecast
from apis.utils import load_parameter

# time is a unix timestamp
CacheKey = namedtuple('CacheKey', ['lat', 'lon', 'time', 'granularity'])


def cache_key_to_string(ck):
    return ','.join(map(str, ck))


class WeatherProvider():
    def __init__(self, darksky_key, wit_key):
        self.darksky_key = darksky_key
        self.wit_key = wit_key
        self.wit_client = Wit(self.wit_key)

        # Create new database
        # TODO: persist cache to and from file OR make this a generic class
        # that this can extend
        self.cache = {}

    def _cache_forecast(self, cache, forecast_result):
        # Push current forecast into both hourly and daily forecasts
        current = forecast_result.currently
        ck = CacheKey(str(forecast_result.latitude), str(
            forecast_result.longitude), current.time, 'minute')
        cache[ck] = json.dumps(current._data)
        ck = CacheKey(str(forecast_result.latitude), str(
            forecast_result.longitude), current.time, 'hour')
        cache[ck] = json.dumps(current._data)
        ck = CacheKey(str(forecast_result.latitude), str(
            forecast_result.longitude), current.time, 'day')
        cache[ck] = json.dumps(current._data)

        if hasattr(forecast_result, 'minutely'):
            # include minutely forecast because people ask things like "what
            # will the weather be in an hour?"
            for minute in forecast_result.minutely:
                ck = CacheKey(str(forecast_result.latitude), str(
                    forecast_result.longitude), minute.time, 'minute')
                cache[ck] = json.dumps(minute._data)

        for hour in forecast_result.hourly:
            ck = CacheKey(str(forecast_result.latitude), str(
                forecast_result.longitude), hour.time, 'hour')
            cache[ck] = json.dumps(hour._data)

        for day in forecast_result.daily:
            ck = CacheKey(str(forecast_result.latitude), str(
                forecast_result.longitude), day.time, 'day')
            cache[ck] = json.dumps(day._data)

    def transform_forecast(self, report, units='us'):
        '''
        Put data in a format ready to be displayed to the user. E.g. 13 -> 13°F, and 0.123 -> 10%
        Everything should be logged in a consistent system of units

        Takes a python object or DataPoint object
        Returns a list of {name, value} objects
        '''

        try:  # convert DataPoint to python object
            report = report._data
        except AttributeError:
            pass

        # TODO: units should be a user setting. https://xkcd.com/2292/
        if units not in ('us', 'metric'):
            raise ValueError('Unrecognized units', units)

        # Map machine-readable summary to human-readable summary
        icon_converter = defaultdict(lambda: 'unknown',
                                     {
                                         'clear-day': 'clear',
                                         'clear-night': 'clear',
                                         'rain': 'rain',
                                         'snow': 'snow',
                                         'sleet': 'sleet',
                                         'wind': 'wind',
                                         'fog': 'fog',
                                         'cloudy': 'cloudy',
                                         'partly-cloudy-day': 'partly cloudy',
                                         'partly-cloudy-night': 'partly cloudy',
                                     })

        relevant_keys = [
            {'name': 'icon', 'transform': lambda icon: icon_converter[icon]},
            {'name': 'temperature', 'transform_us': '{:.0f}°F'.format,
                'transform_metric': lambda t: '{:.0}°C'.format((t - 32) * 5 / 9)},
            {'name': 'temperatureLow', 'transform_us': '{:.0f}°F'.format,
                'transform_metric': lambda t: '{:.0}°C'.format((t - 32) * 5 / 9)},
            {'name': 'temperatureHigh', 'transform_us': '{:.0f}°F'.format,
                'transform_metric': lambda t: '{:.0}°C'.format((t - 32) * 5 / 9)},
            {'name': 'precipProbability',
                'transform': lambda p: '{:.0%}'.format(round(p, 1))},
            {'name': 'precipAccumulation', 'transform_us': '{:.1f} in'.format,
                'transform_metric': lambda p: '{:.1f} cm'.format(p * 2.54)},
            {'name': 'precipTotal', 'transform_us': '{:.1f} in'.format,
                'transform_metric': lambda p: '{:.1f} cm'.format(p * 2.54)},
            {'name': 'precipIntensity',
             'transform_us': lambda p: '{:.2f} in/hr'.format(float(p)),
             'transform_metric': lambda p: '{:.1f} cm/hr'.format(p * 2.54)},
            {'name': 'precipType'},
            {'name': 'humidity',
                'transform': lambda h: '{:.0%}'.format(round(h, 1))},
            {'name': 'windSpeed', 'transform_us': '{:.1f} mph'.format,
                'transform_metric': lambda s: '{:.1f} km/h'.format(s * 1.61)},
            {'name': 'uvIndex'},
            {'name': 'visibility', 'transform_us': '{:.1f} mi'.format,
                'transform_metric': lambda d: '{:.1f} km'.format(d * 1.61)},
        ]

        # transform strings
        result = []
        for key in relevant_keys:
            if key['name'] in report:
                key_name = key['name']
                if 'transform' in key:
                    result.append({
                        'name': key_name,
                        'value': key['transform'](report[key_name])
                    })
                elif 'transform_us' in key and units == 'us':
                    result.append({
                        'name': key_name,
                        'value': key['transform_us'](report[key_name])
                    })
                elif 'transform_metric' in key and units == 'metric':
                    result.append({
                        'name': key_name,
                        'value': key['transform_metric'](report[key_name])
                    })
                else:
                    result.append({
                        'name': key_name,
                        'value': report[key_name]
                    })
        return result

    def current_weather(self, lat, lon):
        now = datetime.now()
        forecast_result = forecast(self.darksky_key, lat, lon)
        current_report = forecast_result.currently._data  # dicts
        daily_report = forecast_result.daily[0]._data
        daily_report.update(current_report)

        return self.transform_forecast(daily_report)

    def aggregate_forecast(self, fc_range):
        '''
        fc_range - a list of darksky.data.DataPoint objects or of dicts

        returns - a dict
        '''

        def most_frequent(fc_range, key):
            '''return the most frequent value of fc_range[i][key] for all i'''
            c = Counter(
                block[key] for block in fc_range if hasattr(
                    block, key)).most_common(1)
            if c:
                return c[0][0]
            else:
                return None

        def get_mean(fc_range, key):
            arr = [getattr(block, key, 0) for block in fc_range]
            if not arr:
                return None
            return sum(arr) / len(arr)

        result = {
            'icon': most_frequent(fc_range, 'icon'),
            'temperatureHigh': max(max(getattr(block, 'temperatureHigh', -1000), getattr(block, 'temperature', -1000)) for block in fc_range),
            'temperatureLow': min(min(getattr(block, 'temperatureLow', 1000), getattr(block, 'temperature', 1000)) for block in fc_range),
            # this isn't actually how probability works, but good enough
            'precipProbability': max(block['precipProbability'] for block in fc_range),
            'precipAccumulation': sum(getattr(block, 'precipAccumulation', 0) for block in fc_range),
            'precipTotal': sum(getattr(block, 'precipIntensity', 0) for block in fc_range) / float(len(fc_range)) * (fc_range[-1].time - fc_range[0].time) / 60 / 60,
            'precipType': most_frequent(fc_range, 'precipType'),
            'humidity': get_mean(fc_range, 'humidity'),
            'windSpeed': get_mean(fc_range, 'windSpeed'),
            'visibility': get_mean(fc_range, 'visibility'),
            'uvIndex': get_mean(fc_range, 'uvIndex')
        }

        # Delete keys with unset values
        result = {k: v for k, v in result.items() if v is not None}

        return result

    def weather_at_time(self, lat, lon, time_query):
        '''
        Fetch the weather at a specified location and time (between now and 7 days from now).
        The future limit is because Darksky's forecast only extends that far.
        It doesn't support times in the past because 1) it's not a common use case, and 2) implementing it for ranges of >1 day (e.g. last week) would require making multiple requests and more code
        If desired, look at the time='whatever' parameter in darkskylib

        lat, lon - floats
        time_query - a string with a relative time. Something like 'tonight at 8' is fine

        note: you should ensure that wit.ai app's timezone is set to GMT
        darksky returns forecasts in local times without a timezone
        '''

        # find date/time with wit.ai and duckling
        response = self.wit_client.message(time_query)['entities']

        if not response['datetime']:
            raise ValueError('could not parse time, <{}>'.format(time_query))
        else:
            # assume that time_query only contains one datetime object, but
            # duckling is pretty good about handling ranges
            time_instance = response['datetime'][0]

        # parse a wit.ai datetime object, which should look like:
        #     {
        #         'type': 'value',
        #         'grain': 'second' | minute' | 'hour' | 'day' | 'week' | 'year'
        #         'value': '2020-01-01T12:30:00.000+00:00'
        #     }
        # OR an interval containing a start and end that each look like the
        # above
        is_interval = False
        if time_instance['type'] == 'interval':
            # for queries like "this weekend", the result will be a range.
            # just use the start time.
            start_dt = datetime.strptime(
                time_instance['from']['value'],
                "%Y-%m-%dT%H:%M:%S.%f+00:00")
            end_dt = datetime.strptime(
                time_instance['to']['value'],
                "%Y-%m-%dT%H:%M:%S.%f+00:00")
            grain = time_instance['from']['grain']

            is_interval = True
        elif time_instance['type'] == 'value':
            start_dt = datetime.strptime(
                time_instance['value'],
                "%Y-%m-%dT%H:%M:%S.%f+00:00")
            grain = time_instance['grain']

            if grain == 'week':
                end_dt = start_dt + timedelta(days=7)
                is_interval = True
        else:
            raise Exception('unrecognized type', time_instance['type'])

        # Get the full forecast that corresponds to the time granularity
        fc = forecast(self.darksky_key, lat, lon, extend='hourly')
        if grain == 'second' or grain == 'minute':
            try:
                # minutely forecasts are only available in some parts of the
                # world. test if they work
                fc_range = fc.minutely
                # they also don't always include temperature, so test this too
                _temperature_test = fc.minutely[0].temperature
            except AttributeError:
                fc_range = fc.hourly
                grain = 'hour'
        elif grain == 'hour':
            fc_range = fc.hourly
        elif grain == 'day' or grain == 'week' or grain == 'month' or grain == 'year':
            fc_range = fc.daily

        try:
            summary = fc_range.summary
        except AttributeError:
            summary = fc_range[0].summary

        # if we parsed an interval, create an aggregate forecast
        if is_interval:
            # trim the ends of the range. note: darksky only provides hourly
            # forecasts for the next 48 hours, and daily forecasts for the next
            # week
            fc_filtered_range = [block for block in fc_range if start_dt.timestamp(
            ) <= block.time <= end_dt.timestamp()]
            aggregate_fc = self.aggregate_forecast(fc_filtered_range)

            transformed_forecast = self.transform_forecast(aggregate_fc)
            return transformed_forecast + [
                {'name': 'summary', 'value': summary},
                {'name': 'start_date',
                 'value': start_dt.strftime('%a, %b %d')},
                {'name': 'start_time', 'value': start_dt.strftime('%H:%M')},
                {'name': 'end_date', 'value': end_dt.strftime('%a, %b %d')},
                {'name': 'end_time', 'value': end_dt.strftime('%H:%M')},
                {'name': 'grain', 'value': grain},
            ]

        else:
            # return the forecast for that time
            transformed_forecast = self.transform_forecast(fc.currently)
            return transformed_forecast + [
                {'name': 'summary', 'value': summary},
                {'name': 'date', 'value': start_dt.strftime('%a, %b %d')},
                {'name': 'time', 'value': start_dt.strftime('%H:%M')},
                {'name': 'grain', 'value': grain},
            ]

        return timestamp

    def rate_satisfaction(self):
        return []

    def __repr__(self):
        '''For executable logs to work, `repr` must generate an executable initialization of this class'''
        return 'WeatherInterface(keys["darksky"], keys["wit_date"])'
