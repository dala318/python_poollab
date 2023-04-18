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


class WaterTreatmentProduct(object):
    id = None
    name = ""
    effect = ""
    phrase = ""

    def __init__(self, data) -> None:
        for key, value in data.items():
            setattr(self, key, value)


class CloudAccount:
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


async def api(token):
    transport = AIOHTTPTransport(url=API_ENDPOINT, headers={"Authorization": token})
    async with Client(
        transport=transport, fetch_schema_from_transport=False  # Only for building GQL
    ) as session:
        query = gql(QUERY_SCHEMA)
        result = await session.execute(query)
        _LOGGER.debug(json.dumps(result, indent=2))
        parsed_result = CloudAccount(result)
        return parsed_result


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

    result = asyncio.run(api(arg_result.token))
    _LOGGER.info(result)
