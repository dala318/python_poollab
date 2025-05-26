"""PoolLab API handler."""

from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Any

API_ENDPOINT = "https://backend.labcom.cloud/graphql"

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

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


@dataclass
class Measurement:
    """Data class for PoolLab measurements."""

    id: int | None = None
    scenario: str = ""
    parameter: str = ""
    parameter_id: str = ""
    unit: str = ""
    comment: str = ""
    device_serial: str = ""
    operator_name: str = ""
    value: str = ""
    formatted_value: str = ""
    ideal_low: str = ""
    ideal_high: str = ""
    ideal_status: str = ""
    timestamp: datetime | None = None
    interpreted_value: float | None = field(
        init=False, default=None, metadata={"internal": True}
    )
    interpreted_oor: bool = field(
        init=False, default=False, metadata={"internal": True}
    )

    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.timestamp, (int, float)):
            self.timestamp = datetime.fromtimestamp(self.timestamp)

        if self.value and self.scenario in MEAS_RANGES_BY_SCENARIO:
            try:
                val = float(self.value)
                min_val, max_val = MEAS_RANGES_BY_SCENARIO[self.scenario]
                self.interpreted_value = max(min(val, max_val), min_val)
                self.interpreted_oor = not (min_val <= val <= max_val)
            except ValueError:
                pass

    @staticmethod
    def get_schema(indent: str) -> str:
        """Return the schema for the Measurement class."""
        return "".join(
            f"{indent}{f.name}\n"
            for f in fields(Measurement)
            if not f.metadata.get("internal", False)
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the Measurement as a dictionary."""
        return self.__dict__.copy()


@dataclass
class Account:
    """Data class for PoolLab accounts."""

    id: int | None = None
    forename: str = ""
    surname: str = ""
    street: str = ""
    zipcode: str = ""
    city: str = ""
    phone1: str = ""
    phone2: str = ""
    fax: str = ""
    email: str = ""
    country: str = ""
    canton: str = ""
    notes: str = ""
    volume: str = ""
    volume_unit: str = ""
    pooltext: str = ""
    gps: str = ""
    Measurements: list[Measurement] = field(default_factory=list)

    def __post_init__(self):
        """Post-initialization processing."""
        self.Measurements = [
            m if isinstance(m, Measurement) else Measurement(**m)
            for m in self.Measurements
        ]

    @property
    def full_name(self) -> str:
        """Return the full name of the account holder."""
        return f"{self.forename} {self.surname}".strip()

    @staticmethod
    def get_schema(indent: str = "") -> str:
        """Return the schema for the Account class."""
        schema = ""
        for f in fields(Account):
            if f.name == "Measurements":
                schema += f"{indent}Measurements {{\n"
                schema += Measurement.get_schema(indent + "  ")
                schema += f"{indent}}}\n"
            else:
                schema += f"{indent}{f.name}\n"
        return schema

    def as_dict(self) -> dict[str, Any]:
        """Return the Account as a dictionary."""
        return self.__dict__.copy()


@dataclass
class WaterTreatmentProduct:
    """Data class for PoolLab water treatment products."""

    id: int = None
    name: str = ""
    effect: str = ""
    phrase: str = ""

    def __post_init__(self):
        """Post-initialization processing."""
        pass  # Nothing special for now, can keep or drop

    @staticmethod
    def get_schema(indent: str) -> str:
        """Return the schema for the WaterTreatmentProduct class."""
        return "".join(f"{indent}{f.name}\n" for f in fields(WaterTreatmentProduct))

    def as_dict(self) -> dict[str, Any]:
        """Return the WaterTreatmentProduct as a dictionary."""
        return self.__dict__.copy()


@dataclass
class CloudAccount:
    """Data class for PoolLab cloud account."""

    id: int = None
    email: str = ""
    last_change_time: datetime | None = None
    last_wtp_change: datetime | None = None
    Accounts: list[Account] = field(default_factory=list)
    WaterTreatmentProducts: list[WaterTreatmentProduct] = field(default_factory=list)

    def __init__(self, data: dict[str, Any]):
        """Initialize the CloudAccount from a dictionary."""
        if cloud_data := data.get("CloudAccount"):
            self.id = cloud_data.get("id")
            self.email = cloud_data.get("email")
            self.last_change_time = (
                datetime.fromtimestamp(cloud_data["last_change_time"])
                if "last_change_time" in cloud_data
                else None
            )
            self.last_wtp_change = (
                datetime.fromtimestamp(cloud_data["last_wtp_change"])
                if "last_wtp_change" in cloud_data
                else None
            )
            self.Accounts = [Account(**a) for a in cloud_data.get("Accounts", [])]
            self.WaterTreatmentProducts = [
                WaterTreatmentProduct(**w)
                for w in cloud_data.get("WaterTreatmentProducts", [])
            ]

    def get_measurement(self, account_id: int, meas_param: str) -> Measurement:
        """Get the latest measurement for a given account and parameter."""
        account = next(x for x in self.Accounts if x.id == account_id)
        sorted_meas = sorted(
            account.Measurements, key=lambda x: x.timestamp, reverse=True
        )
        return next(x for x in sorted_meas if x.parameter == meas_param)

    @staticmethod
    def get_schema(indent: str) -> str:
        """Return the schema for the CloudAccount class."""
        schema = ""
        for attr in [
            "id",
            "email",
            "last_change_time",
            "last_wtp_change",
            "Accounts",
            "WaterTreatmentProducts",
        ]:
            if attr == "Accounts":
                schema += f"{indent}Accounts {{\n"
                schema += Account.get_schema(indent + "  ")
                schema += f"{indent}}}\n"
            elif attr == "WaterTreatmentProducts":
                schema += f"{indent}WaterTreatmentProducts {{\n"
                schema += WaterTreatmentProduct.get_schema(indent + "  ")
                schema += f"{indent}}}\n"
            else:
                schema += f"{indent}{attr}\n"
        return schema

    def as_dict(self) -> dict[str, Any]:
        """Return the CloudAccount as a dictionary."""
        return self.__dict__.copy()


class PoolLabApi:
    """Public API class for PoolLab."""

    def __init__(self, token: str, url: str = API_ENDPOINT, ssl: bool = True) -> None:
        """Init the cloud api object."""
        self._token = token
        self._data = None
        self._url = url
        self._ssl = ssl

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
            url=self._url, headers={"Authorization": self._token}, ssl=self._ssl
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
