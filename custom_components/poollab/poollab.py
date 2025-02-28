"""PoolLab API handler."""

from datetime import datetime
from typing import Any

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

API_ENDPOINT = "https://production.backend.labcom.cloud/graphql"

# Measurement ranges according to https://poollab.org/static/manuals/poollab_manual_gb-fr-e-d-i.pdf
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


class Measurement(object):
    """Data class for decoded water measurement."""

    id = None
    scenario = ""
    parameter = ""
    parameter_id = ""
    unit = ""
    comment = ""
    device_serial = ""
    operator_name = ""
    value = ""
    formatted_value = ""
    ideal_low = ""
    ideal_high = ""
    ideal_status = ""
    timestamp = None

    def __init__(self, data: dict[str, Any]) -> None:
        """Init the measurement object."""
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

    @staticmethod
    def get_schema(indent: str) -> str:
        """Return the schema for the measurement object."""
        schema = ""
        for attribute in Measurement.__dict__:
            if attribute[:2] != "__":
                value = getattr(Measurement, attribute)
                if not callable(value):
                    schema += indent + str(attribute) + "\n"
        return schema


class Account(object):
    """Data class for decoded account data."""

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
    volume_unit = ""
    pooltext = ""
    gps = ""
    Measurements = []

    def __init__(self, data: dict[str, Any]) -> None:
        """Init the account object."""
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

    @staticmethod
    def get_schema(indent: str) -> str:
        """Return the schema for the account object."""
        schema = ""
        for attribute in Account.__dict__:
            if attribute[:2] != "__":
                value = getattr(Account, attribute)
                if not callable(value):
                    if attribute == "Measurements":
                        schema += indent + "Measurements {\n"
                        schema += Measurement.get_schema(indent + "  ")
                        schema += indent + "}\n"
                    elif attribute == "full_name":
                        pass
                    else:
                        schema += indent + str(attribute) + "\n"
        return schema


class WaterTreatmentProduct(object):
    """Data class for decoded water treatment products."""

    id = None
    name = ""
    effect = ""
    phrase = ""

    def __init__(self, data: dict[str, Any]) -> None:
        """Init the water treatment product object."""

        for key, value in data.items():
            setattr(self, key, value)

    @staticmethod
    def get_schema(indent: str) -> str:
        """Return the schema for the water treatment product object."""
        schema = ""
        for attribute in WaterTreatmentProduct.__dict__:
            if attribute[:2] != "__":
                value = getattr(WaterTreatmentProduct, attribute)
                if not callable(value):
                    schema += indent + str(attribute) + "\n"
        return schema


class CloudAccount:
    """Master class for PoolLab data."""

    id = None
    email = ""
    last_change_time = None
    last_wtp_change = None
    Accounts = []
    WaterTreatmentProducts = []

    def __init__(self, data: dict[str, Any]) -> None:
        """Init the clound account object."""

        if data := data.get("CloudAccount"):
            # data = data["CloudAccount"]
            for key, value in data.items():
                if key == "Accounts":
                    for a in data["Accounts"]:
                        self.Accounts.append(Account(a))
                elif key == "WaterTreatmentProducts":
                    for w in data["WaterTreatmentProducts"]:
                        self.WaterTreatmentProducts.append(WaterTreatmentProduct(w))
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

    @staticmethod
    def get_schema(indent: str) -> str:
        """Return the schema for the cloud account object."""
        schema = ""
        for attribute in CloudAccount.__dict__:
            if attribute[:2] != "__":
                value = getattr(CloudAccount, attribute)
                if not callable(value):
                    if attribute == "Accounts":
                        schema += indent + "Accounts {\n"
                        schema += Account.get_schema(indent + "  ")
                        schema += indent + "}\n"
                    elif attribute == "WaterTreatmentProducts":
                        schema += indent + "WaterTreatmentProducts {\n"
                        schema += WaterTreatmentProduct.get_schema(indent + "  ")
                        schema += indent + "}\n"
                    else:
                        schema += indent + str(attribute) + "\n"
        return schema


class PoolLabApi:
    """Public API class for PoolLab."""

    def __init__(self, token: str) -> None:
        """Init the cloud api object."""
        self._token = token
        self._data = None

    def _build_schema(self) -> str:
        schema = "\n"
        schema += "query getContinents {\n"
        schema += "CloudAccount {\n"
        schema += CloudAccount.get_schema("  ")
        schema += "}}"
        return schema

    async def _update(self, schema: str | None = None) -> bool:
        """Update from the cloud api."""
        if schema is None:
            schema = self._build_schema()
        transport = AIOHTTPTransport(
            url=API_ENDPOINT, headers={"Authorization": self._token}
        )
        async with Client(
            transport=transport,
            fetch_schema_from_transport=False,  # Only for building GQL
        ) as session:
            query = gql(schema)
            result = await session.execute(query)
            if result is not None:
                self._data = result
                return True
        return False

    async def test(self) -> bool:
        """Test the cloud data connection."""
        try:
            if await self._update():
                return True
        except Exception:  # noqa: BLE001
            pass
        return False

    async def request(self, schema: str | None = None) -> CloudAccount:
        """Fetch the cloud data."""
        await self._update(schema)
        if self._data is not None:
            return CloudAccount(self._data)
        return None
