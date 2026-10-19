"""How the chain client meets real providers (decision B-24): Alchemy's refused log range comes back as an HTTP 400
whose body alone says why, and a read just after a write can reach a node that has not seen the write yet."""

import requests

from app.agentwallet import chain

ALCHEMY_400 = ('{"jsonrpc":"2.0","id":1,"error":{"code":-32600,"message":"Under the Free tier plan, you can make '
               'eth_getLogs requests with up to a 10 block range. Based on your parameters, this block range should '
               'work: [0x2e1e8af, 0x2e1e8b8]. Upgrade to PAYG for expanded block range."}}')


def http_error(status: int, body: str) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status
    response._content = body.encode()
    return requests.HTTPError(f"{status} Client Error: Bad Request for url: https://base-sepolia.example/v2/k3y",
                              response=response)


def test_a_range_refused_in_the_response_body_is_halved():
    assert chain._range_refused(http_error(400, ALCHEMY_400))


def test_a_rate_limit_or_a_bare_400_is_not_a_refused_range():
    busy = '{"error":{"code":429,"message":"Your app has exceeded its compute units per second capacity."}}'
    assert not chain._range_refused(http_error(429, busy))
    assert not chain._range_refused(http_error(400, '{"error":{"message":"invalid argument"}}'))


class FakeEth:
    def __init__(self, heights):
        self.heights = list(heights)
        self.asked = 0

    @property
    def block_number(self):
        self.asked += 1
        return self.heights.pop(0) if len(self.heights) > 1 else self.heights[0]


def settling_client(chain_id: int, heights) -> chain.VaultClient:
    client = chain.VaultClient.__new__(chain.VaultClient)  # no endpoint needed
    client.chain_id = chain_id
    client.w3 = type("W3", (), {"eth": FakeEth(heights)})()
    return client


def test_after_a_write_reads_wait_for_the_endpoint_to_pass_the_receipt(monkeypatch):
    monkeypatch.setattr(chain.time, "sleep", lambda seconds: None)
    client = settling_client(84532, [100, 100, 101, 102])
    client.settle(100)
    assert client.w3.eth.asked == 4  # returned once the endpoint reported block 102, two past the receipt


def test_anvil_has_one_node_and_never_waits():
    client = settling_client(chain.ANVIL_CHAIN_ID, [100])
    client.settle(100)
    assert client.w3.eth.asked == 0
