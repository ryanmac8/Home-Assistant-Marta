"""Platform for sensor integration."""
import logging
import voluptuous as vol

import requests
import re
from bs4 import BeautifulSoup
from datetime import timedelta

from homeassistant.const import (CONF_FRIENDLY_NAME,CONF_STATE)
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv


MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)

_LOGGER = logging.getLogger(__name__)
CONF_CARDNUMBER = 'card_number'

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_CARDNUMBER): cv.string,
    vol.Optional(CONF_FRIENDLY_NAME): cv.string,
    vol.Optional(CONF_STATE, default="trips"): vol.In(['trips', 'value']),
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    cardnumber=config.get(CONF_CARDNUMBER)
    friendly_name=config.get(CONF_FRIENDLY_NAME)
    state_type=config.get(CONF_STATE)
    add_entities([MartaCard(cardnumber,friendly_name,state_type)])


class MartaCard(Entity):
    """Representation of a Sensor."""

    def __init__(self, cardnumber, friendly_name,state_type):
        """Initialize the sensor."""
        self._state = None
        self._cardnumber=cardnumber
        self._friendly_name=friendly_name
        self._state_type=state_type
        self._attributes={}

    @property
    def entity_id(self):
        """Return the name of the sensor."""
        name="sensor.marta_card_"+self._cardnumber[-4:]
        return name


    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def name(self):
        """Return the fname of the sensor."""
        return self._friendly_name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if(self._state_type=="trips"):
            measurement="Trips"
        else:
            measurement=""
        return measurement

    @property
    def icon(self):
        """Return the icon."""
        return "mdi:subway-variant"



    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return self._attributes

    # @property
    # def unit_of_measurement(self):
    #     """Return the unit of measurement."""
    #     return TEMP_CELSIUS
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        data = {'cardnumber':self._cardnumber,
                'submitButton.x':'32',
                'submitButton.y':'5'}

        i = requests.post('https://balance.breezecard.com/breezeWeb/cardnumber_qa.do', data = data)
        root = BeautifulSoup(i.text, 'html.parser')

        trip_count=0

        #Default Get Stored Values
        storedvalue=root.find('td', text="Stored Value : ")
        stored_value=storedvalue.find_next('td').text
        if(stored_value.isspace() or stored_value==""):
            stored_value=0
        stored_trips=storedvalue.find_next('td').find_next('td').text
        if(stored_trips.isspace() or stored_trips==""):
            stored_trips=0
        trip_count=trip_count+stored_trips

        product_top_level=root.find('td', text="Remaining Rides").find_next('tr')
        loop = 0
        while loop == 0:
            row = product_top_level.findAll('td')
            if(len(row)<2):
                product_top_level=product_top_level.find_next('tr')
                continue
            item_name=product_top_level.find_next('td').text
            if(item_name=="Stored Value : "):
                loop=1
                break
            item_value=product_top_level.find_next('td').find_next('td').text
            item_trip=product_top_level.find_next('td').find_next('td').find_next('td').text
            if(item_value.isspace() or item_value==""):
                item_value=0
            if(item_trip.isspace() or item_trip==""):
                item_trip=0
            if("Trip" in item_name):
                trip_count=trip_count+int(item_trip)
            if(item_value!=0 and "Trip" not in item_name):
                item_name=item_name.replace(" ", "_").lower()
                self._attributes[item_name+"_value"] = item_value
            if(item_trip!=0 and "Trip" not in item_name):
                item_name=item_name.replace(" ", "_").lower()
                self._attributes[item_name+"_trips"] = item_trip
            #move to next TR
            product_top_level=product_top_level.find_next('tr')

        #Write Default Card Status
        if (self._state_type=="value"):
            self._state = stored_dollar_value
        if (self._state_type=="trips"):
            self._state = trip_count
        self._attributes["card_number"]=self._cardnumber
        self._attributes["stored_value"]=stored_value
        self._attributes["stored_trips"]=trip_count
