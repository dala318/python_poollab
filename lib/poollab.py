import asyncio
import argparse
from datetime import datetime
import json
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
    pooltext
    gps
    Measurements {
      id
      scenario
      parameter
      unit
      comment
      device_serial
      operator_name
      value
      ideal_low
      ideal_high
      timestamp
    }
  }
  WaterTreatmentProducts {
    id
    name
    effect
    phrase
  }
}}"""


logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


# def try_set_attr(key: str, data, target) -> bool:
#     try:
#         setattr(target, key, data[key])
#     except Exception as e:
#         return False
#     return True


class Measurement(object):
    """Data class for decoded water measurement"""

    id = None
    scenario = ""
    parameter = ""
    unit = ""
    comment = ""
    device_serial = ""
    operator_name = ""
    value = ""
    ideal_low = ""
    ideal_high = ""
    timestamp = None

    def __init__(self, data) -> None:
        for key, value in data.items():
            if "timestamp" in key:
                setattr(self, key, datetime.fromtimestamp(value))
            else:
                setattr(self, key, value)


class Account(object):
    """Data class for decoded account data"""

    id = None
    forename = ""
    surname = ""
    street = ""
    zipcode = ""
    city = ""
    phone1 = ""
    phone2 = ""
    fax = ""
    email = ""
    country = ""
    canton = ""
    notes = ""
    volume = ""
    pooltext = ""
    gps = ""
    Measurements = []

    def __init__(self, data) -> None:
        for key, value in data.items():
            if key == "Measurements":
                for m in data["Measurements"]:
                    self.Measurements.append(Measurement(m))
            else:
                setattr(self, key, value)

    @property
    def full_name(self) -> str:
        """Compiled full name of account"""
        _full_name = ""
        if self.forename:
            _full_name += self.forename
        if self.surname:
            if _full_name:
                _full_name += " "
            _full_name += self.surname
        return _full_name


class WaterTreatmentProduct(object):
    """Data class for decoded water treatment producs"""

    id = None
    name = ""
    effect = ""
    phrase = ""

    def __init__(self, data) -> None:
        for key, value in data.items():
            setattr(self, key, value)


class CloudAccount:
    """Master class for PoolLab data"""

    id = None
    email = ""
    last_change_time = None
    last_wtp_change = None
    Accounts = []

    def __init__(self, data) -> None:
        if "CloudAccount" in data.keys():
            data = data["CloudAccount"]
            # try_set_attr('id', data, self)
            for key, value in data.items():
                if key == "Accounts":
                    for a in data["Accounts"]:
                        self.Accounts.append(Account(a))
                elif "last" in key:
                    setattr(self, key, datetime.fromtimestamp(value))
                else:
                    setattr(self, key, value)


class PoolLabApi:
    """Public API class for PoolLab"""

    def __init__(self, token: str) -> None:
        self._token = token
        self._latest_measurement = None

    async def _query(self) -> bool:
        transport = AIOHTTPTransport(
            url=API_ENDPOINT, headers={"Authorization": self._token}
        )
        async with Client(
            transport=transport,
            fetch_schema_from_transport=False,  # Only for building GQL
        ) as session:
            query = gql(QUERY_SCHEMA)
            result = await session.execute(query)
            # _LOGGER.debug(json.dumps(result, indent=2))
            # _LOGGER.debug(json.dumps(result))
            if result is not None:
                self._latest_measurement = result
                return True
        return False

    async def test(self) -> bool:
        """Testing the cloud data connection"""
        try:
            if await self._query():
                return True
        except Exception:
            pass
        return False

    async def update(self) -> bool:
        """Fetch data from API and store"""
        return await self._query()

    async def request(self) -> CloudAccount:
        """Fetching the cloud data"""
        await self._query()
        if self._latest_measurement is not None:
            return CloudAccount(self._latest_measurement)
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
