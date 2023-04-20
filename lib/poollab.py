"""PoolLab API handler"""
import argparse
import asyncio
import logging
from datetime import datetime

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


class Measurement(object):
    """Data class for decoded water measurement"""

    def __init__(self, data) -> None:
        self.id = None
        self.scenario = ""
        self.parameter = ""
        self.unit = ""
        self.comment = ""
        self.device_serial = ""
        self.operator_name = ""
        self.value = ""
        self.ideal_low = ""
        self.ideal_high = ""
        self.timestamp = None

        for key, value in data.items():
            if "timestamp" in key:
                setattr(self, key, datetime.fromtimestamp(value))
            else:
                setattr(self, key, value)


class Account(object):
    """Data class for decoded account data"""

    def __init__(self, data) -> None:
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

    def __init__(self, data) -> None:
        self.id = None
        self.name = ""
        self.effect = ""
        self.phrase = ""

        for key, value in data.items():
            setattr(self, key, value)


class CloudAccount:
    """Master class for PoolLab data"""

    def __init__(self, data) -> None:
        self.id = None
        self.email = ""
        self.last_change_time = None
        self.last_wtp_change = None
        self.Accounts = []

        if "CloudAccount" in data.keys():
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
        account = next((x for x in self.Accounts if x.id == account_id))
        sorted_meas = sorted(
            account.Measurements, key=lambda x: x.timestamp, reverse=True
        )
        return next((x for x in sorted_meas if x.parameter == meas_param))


class PoolLabApi:
    """Public API class for PoolLab"""

    def __init__(self, token: str) -> None:
        self._token = token
        self._data = None

    async def update(self) -> bool:
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
        """Testing the cloud data connection"""
        try:
            if await self.update():
                return True
        except Exception:
            pass
        return False

    async def request(self) -> CloudAccount:
        """Fetching the cloud data"""
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
