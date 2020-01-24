"""Platform for sensor integration."""
import logging
import voluptuous as vol

import requests
import re
from bs4 import BeautifulSoup
from datetime import timedelta

from homeassistant.const import (CONF_FRIENDLY_NAME, CONF_MONITORED_CONDITIONS,CONF_STATE)
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
    vol.Optional(CONF_MONITORED_CONDITIONS, default=None):
        vol.All(cv.ensure_list)
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    cardnumber=config.get(CONF_CARDNUMBER)
    friendly_name=config.get(CONF_FRIENDLY_NAME)
    monitor=config.get(CONF_MONITORED_CONDITIONS)
    state_type=config.get(CONF_STATE)
    add_entities([MartaCard(cardnumber,friendly_name,monitor,state_type)])


class MartaCard(Entity):
    """Representation of a Sensor."""

    def __init__(self, cardnumber, friendly_name,monitor,state_type):
        """Initialize the sensor."""
        self._state = None
        self._cardnumber=cardnumber
        self._friendly_name=friendly_name
        self._monitor=monitor
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
        #Default Get Stored Values
        storedvalue=root.find('td', text="Stored Value : ")
        stored_value=storedvalue.find_next('td').text
        if(stored_value.isspace() or stored_value==""):
            stored_value=0
        stored_trips=storedvalue.find_next('td').find_next('td').text
        if(stored_trips.isspace() or stored_trips==""):
            stored_trips=0
        #Write Default Card Status
        if (self._state_type=="value"):
            self._state = stored_dollar_value
        if (self._state_type=="trips"):
            self._state = stored_trips
        self._attributes["card_number"]=self._cardnumber
        self._attributes["stored_value"]=stored_value
        self._attributes["stored_trips"]=stored_trips

        # For custom fields, search and post to attributes the value / trip info.
        for monitor in self._monitor:
            pattern = re.compile(monitor)
            monitor=monitor.replace(" ", "_").lower()
            storedvalue=root.find('td', text=pattern)
            self._attributes[monitor+"_value"] = storedvalue.find_next('td').text
            if(self._attributes[monitor+"_value"].isspace() or self._attributes[monitor+"_value"]==""):
                self._attributes[monitor+"_value"]=0
            self._attributes[monitor+"_trips"] = storedvalue.find_next('td').find_next('td').text
            if(self._attributes[monitor+"_trips"].isspace() or self._attributes[monitor+"_trips"]==""):
                self._attributes[monitor+"_trips"]=0
