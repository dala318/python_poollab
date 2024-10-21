"""PoolLab API handler."""

import argparse
import asyncio
from datetime import datetime
import logging

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

API_ENDPOINT = "https://backend.labcom.cloud/graphql"

QUERY_SCHEMA = """
query getContinents {
CloudAccount {
  id
  email
  last_change_time
  last_wtp_change
  Accounts {
  id
    forename
    surname
    street
    zipcode
    city
    phone1
    phone2
    fax
    email
    country
    canton
    notes
    volume
    volume_unit
    pooltext
    gps
    Measurements {
      id
      scenario
      parameter
      parameter_id
      unit
      comment
      device_serial
      operator_name
      value
      formatted_value
      ideal_low
      ideal_high
      ideal_status
      timestamp
    }
  }
  WaterTreatmentProducts {
    id
    name
    effect
    phrase
  }
#   Scenarios {
#     scenario_id
#     Scenario {
#       id
#       name
#       group_id
#       group
#       device_type
#     }
#   }
}}"""

# Measurment ranges according to https://poollab.org/static/manuals/poollab_manual_gb-fr-e-d-i.pdf
MEAS_RANGES_BY_SCENARIO = {
    # Active oxygene 0-30
    # (not tested) "PL O₂": [0, 30],
    # Cyanuric Acid 0-160
    "431-Cyanuric-Acid": [0, 160],  # "parameter":"PL Cyanuric Acid"
    # Alkalinity 0-200
    "430-Total-Alkalinity": [0, 200],  # "parameter":"PL T-Alka"
    # Bromine (tablet) 0-18 ppm (mg/l)
    # Bromine (liquid) 0-9 ppm (mg/l)
    # Calcium Hardness 0-500 ppm (mg/l)
    # Chlorine (tablet) 0-8 ppm (mg/l)
    "428-Chlorine-Free": [0, 8],  # "parameter":"PL Chlorine Free"
    "421-Chlorine-Total": [0, 8],  # "parameter":"PL Chlorine Total"
    # Chlorine (liquid) 0-4 ppm (mg/l)
    # Chlorine dioxide (tablet) 0-15 ppm (mg/l)
    # Chlorine dioxide (liquid) 0-7.6 ppm (mg/l)
    # LR Hydrogen Peroxide 0-2.9 ppm (mg/l)
    # HR Hydrogen Peroxide 0-200 ppm (mg/l)
    # Ozone (tablet) 0-5.4 ppm (mg/l)
    # Ozone (liquid) 0-2.7 ppm (mg/l)
    # pH (tablet) 6.5-8.4
    "429-pH-PoolLab": [6.5, 8.4],  # "parameter":"PL pH"
    # pH (tablet) 6.5-8.4
    # PHMB 5-60
    # Total Hardness 0-500
    # Urea 0.1-2.5
}


logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


class Measurement(object):
    """Data class for decoded water measurement."""

    def __init__(self, data) -> None:
        """Init the measurement object."""
        self.id = None
        self.scenario = ""
        self.parameter = ""
        self.parameter_id = ""
        self.unit = ""
        self.comment = ""
        self.device_serial = ""
        self.operator_name = ""
        self.value = ""
        self.formatted_value = ""
        self.ideal_low = ""
        self.ideal_high = ""
        self.ideal_status = ""
        self.timestamp = None

        for key, value in data.items():
            if "timestamp" in key:
                setattr(self, key, datetime.fromtimestamp(value))
            else:
                setattr(self, key, value)

        self.interpreted_value = None
        self.interpreted_oor = False
        if self.value and self.scenario in MEAS_RANGES_BY_SCENARIO:
            try:
                value = float(self.value)
                range_min = MEAS_RANGES_BY_SCENARIO[self.scenario][0]
                range_max = MEAS_RANGES_BY_SCENARIO[self.scenario][1]
                if value < range_min:
                    self.interpreted_value = float(range_min)
                    self.interpreted_oor = True
                elif value > range_max:
                    self.interpreted_value = float(range_max)
                    self.interpreted_oor = True
                else:
                    self.interpreted_value = value
            except:  # noqa: E722
                pass


class Account(object):
    """Data class for decoded account data."""

    def __init__(self, data) -> None:
        """Init the account object."""
        self.id = None
        self.forename = ""
        self.surname = ""
        self.street = ""
        self.zipcode = ""
        self.city = ""
        self.phone1 = ""
        self.phone2 = ""
        self.fax = ""
        self.email = ""
        self.country = ""
        self.canton = ""
        self.notes = ""
        self.volume = ""
        self.volume_unit = ""
        self.pooltext = ""
        self.gps = ""
        self.Measurements = []
        for key, value in data.items():
            if key == "Measurements":
                for m in data["Measurements"]:
                    self.Measurements.append(Measurement(m))
            else:
                setattr(self, key, value)

    @property
    def full_name(self) -> str:
        """Compiled full name of account."""
        _full_name = ""
        if self.forename:
            _full_name += self.forename
        if self.surname:
            if _full_name:
                _full_name += " "
            _full_name += self.surname
        return _full_name


class WaterTreatmentProduct(object):
    """Data class for decoded water treatment producs."""

    def __init__(self, data) -> None:
        """Init the water treatment product object."""
        self.id = None
        self.name = ""
        self.effect = ""
        self.phrase = ""

        for key, value in data.items():
            setattr(self, key, value)


class CloudAccount:
    """Master class for PoolLab data."""

    def __init__(self, data) -> None:
        """Init the clound account object."""
        self.id = None
        self.email = ""
        self.last_change_time = None
        self.last_wtp_change = None
        self.Accounts = []

        if "CloudAccount" in data:
            data = data["CloudAccount"]
            for key, value in data.items():
                if key == "Accounts":
                    for a in data["Accounts"]:
                        self.Accounts.append(Account(a))
                elif "last" in key:
                    setattr(self, key, datetime.fromtimestamp(value))
                else:
                    setattr(self, key, value)

    def get_measurement(self, account_id: int, meas_param: str):
        """Get a measurement."""
        account = next(x for x in self.Accounts if x.id == account_id)
        sorted_meas = sorted(
            account.Measurements, key=lambda x: x.timestamp, reverse=True
        )
        return next(x for x in sorted_meas if x.parameter == meas_param)


class PoolLabApi:
    """Public API class for PoolLab."""

    def __init__(self, token: str) -> None:
        """Init the cloud api object."""
        self._token = token
        self._data = None

    async def update(self) -> bool:
        """Update fron the cloud api."""
        transport = AIOHTTPTransport(
            url=API_ENDPOINT, headers={"Authorization": self._token}
        )
        async with Client(
            transport=transport,
            fetch_schema_from_transport=False,  # Only for building GQL
        ) as session:
            query = gql(QUERY_SCHEMA)
            result = await session.execute(query)
            if result is not None:
                self._data = result
                return True
        return False

    async def test(self) -> bool:
        """Test the cloud data connection."""
        try:
            if await self.update():
                return True
        except Exception:  # noqa: BLE001
            pass
        return False

    async def request(self) -> CloudAccount:
        """Fetch the cloud data."""
        await self.update()
        if self._data is not None:
            return CloudAccount(self._data)
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read all data from cloud API")
    parser.add_argument(
        "-t",
        action="store",
        dest="token",
        required=True,
        help="API token (get from https://labcom.cloud/pages/user-setting)",
    )
    arg_result = parser.parse_args()
    poollab_api = PoolLabApi(arg_result.token)
    _LOGGER.info(asyncio.run(poollab_api.request()))
