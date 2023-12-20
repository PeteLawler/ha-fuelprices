"""Config flow for MSFT Family Safety."""

import logging
from typing import Any

from pyfuelprices import SOURCE_MAP
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers import config_validation as cv
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_RADIUS, CONF_NAME

from .const import DOMAIN, NAME

_LOGGER = logging.getLogger(__name__)

AREA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): selector.TextSelector(),
        vol.Required(CONF_RADIUS, default=5.0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="miles",
                min=1,
                max=50,
                step=0.1,
            )
        ),
        vol.Inclusive(
            CONF_LATITUDE, "coordinates", "Latitude and longitude must exist together"
        ): cv.latitude,
        vol.Inclusive(
            CONF_LONGITUDE, "coordinates", "Latitude and longitude must exist together"
        ): cv.longitude,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    configured_areas: list[dict] = []
    configured_sources = []
    configuring_area = {}
    configuring_index = -1

    @property
    def configured_area_names(self) -> list[str]:
        """Return a list of area names."""
        items = []
        for area in self.configured_areas:
            items.append(area["name"])
        return items

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the intial step."""
        # only one config entry allowed
        # users should use the options flow to adjust areas and sources.
        await self.async_set_unique_id(NAME)
        self._abort_if_unique_id_configured()
        return await self.async_step_main_menu()

    async def async_step_main_menu(self, _: None = None):
        """Main menu."""
        return self.async_show_menu(
            step_id="main_menu",
            menu_options={
                "area_menu": "Configure areas to create devices/sensors",
                "sources": "Configure data collector sources",
                "finished": "Complete setup",
            },
        )

    async def async_step_sources(self, user_input: dict[str, Any] | None = None):
        """Sources configuration step."""
        if user_input is not None:
            self.configured_sources = user_input["sources"]
            return await self.async_step_main_menu(None)
        return self.async_show_form(
            step_id="sources",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "sources", default=self.configured_sources
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            options=[k for k in SOURCE_MAP],
                            multiple=True,
                        )
                    )
                }
            ),
        )

    async def async_step_area_menu(self, _: None = None) -> FlowResult:
        """Show the area menu."""
        return self.async_show_menu(
            step_id="area_menu",
            menu_options=[
                "area_create",
                "area_update_select",
                "area_delete",
                "main_menu",
            ],
        )

    async def async_step_area_create(self, user_input: dict[str, Any] | None = None):
        """Handle an area configuration."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.configured_areas.append(
                {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_LATITUDE: user_input[CONF_LATITUDE],
                    CONF_LONGITUDE: user_input[CONF_LONGITUDE],
                    CONF_RADIUS: user_input[CONF_RADIUS],
                }
            )
            return await self.async_step_area_menu()
        return self.async_show_form(
            step_id="area_create", data_schema=AREA_SCHEMA, errors=errors
        )

    async def async_step_area_update_select(
        self, user_input: dict[str, Any] | None = None
    ):
        """Show a menu to allow the user to select what option to update."""
        if user_input is not None:
            for i, data in enumerate(self.configured_areas):
                if self.configured_areas[i]["name"] == user_input[CONF_NAME]:
                    self.configuring_area = data
                    self.configuring_index = i
                    break
            return await self.async_step_area_update()
        if len(self.configured_areas) > 0:
            return self.async_show_form(
                step_id="area_update_select",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_NAME): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                mode=selector.SelectSelectorMode.LIST,
                                options=self.configured_area_names,
                            )
                        )
                    }
                ),
            )
        return await self.async_step_area_menu()

    async def async_step_area_update(self, user_input: dict[str, Any] | None = None):
        """Handle an area update."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.configured_areas.pop(self.configuring_index)
            self.configured_areas.append(
                {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_LATITUDE: user_input[CONF_LATITUDE],
                    CONF_LONGITUDE: user_input[CONF_LONGITUDE],
                    CONF_RADIUS: user_input[CONF_RADIUS],
                }
            )
            return await self.async_step_area_menu()
        return self.async_show_form(
            step_id="area_update",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=self.configuring_area[CONF_NAME]
                    ): selector.TextSelector(),
                    vol.Required(
                        CONF_RADIUS, default=self.configuring_area[CONF_RADIUS]
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="miles",
                            min=1,
                            max=50,
                            step=0.1,
                        )
                    ),
                    vol.Inclusive(
                        CONF_LATITUDE,
                        "coordinates",
                        "Latitude and longitude must exist together",
                        default=self.configuring_area[CONF_LATITUDE],
                    ): cv.latitude,
                    vol.Inclusive(
                        CONF_LONGITUDE,
                        "coordinates",
                        "Latitude and longitude must exist together",
                        default=self.configuring_area[CONF_LONGITUDE],
                    ): cv.longitude,
                }
            ),
            errors=errors,
        )

    async def async_step_area_delete(self, user_input: dict[str, Any] | None = None):
        """Delete a configured area."""
        if user_input is not None:
            for i, data in enumerate(self.configured_areas):
                if data["name"] == user_input[CONF_NAME]:
                    self.configured_areas.pop(i)
                    break
            return await self.async_step_area_menu()
        if len(self.configured_areas) > 0:
            return self.async_show_form(
                step_id="area_delete",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_NAME): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                mode=selector.SelectSelectorMode.LIST,
                                options=self.configured_area_names,
                            )
                        )
                    }
                ),
            )
        return await self.async_step_area_menu()

    async def async_step_finished(self, user_input: dict[str, Any] | None = None):
        """Final confirmation step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input["sources"] = (
                self.configured_sources
                if len(self.configured_sources) > 0
                else [k for k in SOURCE_MAP]
            )
            user_input["areas"] = self.configured_areas
            return self.async_create_entry(title=NAME, data=user_input)
        return self.async_show_form(
            step_id="finished",
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
