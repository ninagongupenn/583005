
import json
import os
import base64
from urllib.parse import unquote

import requests
from web3 import Web3
from web3.providers.rpc import HTTPProvider


# Ethereum connection using Infura
INFURA_API_KEY = "30be0045f929460db59d87504369455e"

api_url = f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"

provider = HTTPProvider(
    api_url,
    request_kwargs={"timeout": 45}
)

web3 = Web3(provider)


# Bored Ape Yacht Club contract address
contract_address = Web3.to_checksum_address(
    "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"
)


# Load contract ABI
with open(
    os.path.join(os.path.dirname(__file__), "ape_abi.json"),
    "r",
    encoding="utf-8"
) as f:
    abi = json.load(f)


def get_metadata(token_uri):
    # Handle metadata embedded directly in the URI
    if token_uri.startswith("data:application/json;base64,"):
        encoded = token_uri.split(",", 1)[1]
        return json.loads(base64.b64decode(encoded))

    if token_uri.startswith("data:application/json,"):
        encoded = token_uri.split(",", 1)[1]
        return json.loads(unquote(encoded))

    # Convert IPFS URI into HTTP gateway URL
    if token_uri.startswith("ipfs://"):
        path = token_uri.replace("ipfs://", "", 1)
        path = path.removeprefix("ipfs/")

        urls = [
            f"https://ipfs.io/ipfs/{path}",
            f"https://gateway.pinata.cloud/ipfs/{path}",
        ]
    else:
        urls = [token_uri]

    # Retrieve JSON metadata
    for url in urls:
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError):
            continue

    raise RuntimeError("Unable to retrieve NFT metadata")


def get_ape_info(ape_id):
    assert isinstance(ape_id, int), f"{ape_id} is not an int"
    assert 0 <= ape_id, f"{ape_id} must be at least 0"
    assert ape_id <= 9999, f"{ape_id} must be less than 10,000"

    data = {
        "owner": "",
        "image": "",
        "eyes": ""
    }

    # Connect to BAYC contract
    contract = web3.eth.contract(
        address=contract_address,
        abi=abi
    )

    # Get NFT owner from Ethereum
    data["owner"] = contract.functions.ownerOf(ape_id).call()

    # Retrieve NFT token URI
    token_uri = contract.functions.tokenURI(ape_id).call()

    # Fetch NFT metadata
    metadata = get_metadata(token_uri)

    # Extract image
    data["image"] = metadata["image"]

    # Extract eyes attribute
    for attribute in metadata["attributes"]:
        if attribute.get("trait_type") == "Eyes":
            data["eyes"] = attribute["value"]
            break

    assert isinstance(data, dict)
    assert all(
        key in data for key in ["owner", "image", "eyes"]
    )

    return data


if __name__ == "__main__":
    print(get_ape_info(8585))
