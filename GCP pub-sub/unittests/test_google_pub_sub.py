# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import json
import sys
from unittest import mock
import unittest

sys.modules["chronicle.ingest"] = mock.Mock()
from PUBSUB import main

@mock.patch("PUBSUB.main.ingest")
class TestGooglePubSubBuildPayload(unittest.TestCase):
    """Test cases to verify the functioning of "build_payload" function"""

    # Set variables values
    main.PAYLOAD_SIZE = 0
    main.PAYLOAD = []
    main.CHRONICLE_DATA_TYPE = "LOGS"

    log_1 = {str(key): "test "+ str(key) for key in range(1, 1000)} # 18814 bytes
    log_2 = {str(key): "test "+ str(key) for key in range(1, 2000)} # 39814 bytes
    log_3 = {str(key): "test "+ str(key) for key in range(1, 22000)} # 483814 bytes

    def test_build_payload_1(self, mocked_ingest):
        """Test case to verify build a new Payload if the the Payload Size is 0."""
        main.build_payload(log=self.log_1)

        self.assertEqual(mocked_ingest.call_count, 0)
        self.assertEqual(main.PAYLOAD, [json.dumps(self.log_1)])

    def test_build_payload_2(self, mocked_ingest):
        """Test case to verify we store logs in the Payload of the log length is not more than 500 Kb."""
        main.build_payload(log=self.log_2)

        self.assertEqual(mocked_ingest.call_count, 0)
        self.assertEqual(main.PAYLOAD, [json.dumps(self.log_1), json.dumps(self.log_2)])

    def test_build_payload_3(self, mocked_ingest):
        """Test case to verify we ingest all the logs if the cumulative sum of logs
        is greater than 500 Kb and update the Payload with current set of logs."""
        main.build_payload(log=self.log_3)

        self.assertEqual(mocked_ingest.call_count, 1)
        mocked_ingest.assert_called_with([json.dumps(self.log_1), json.dumps(self.log_2)], "LOGS")
        self.assertEqual(main.PAYLOAD, [json.dumps(self.log_3)])

class MockMessage:
    """Mock class for subscriber message."""
    def __init__(self, data):
        self.data = data.encode()

    def ack(self):
        print("ACK revieved")

class MockFuture:
    """Mock class for future object."""
    def __init__(self, callback, data):
        self.callback = callback
        self.data = data

    def result(self, *args, **kwargs):
        self.callback(MockMessage(data=self.data))

    def cancel(self):
        pass

def mocked_subscribe(*args, **kwargs):
    """Return future object which calls callback function on request."""
    return MockFuture(callback=kwargs.get("callback"), data='{"id": 1, "type": "Sensor data"}')

def mocked_subscribe_value_error(*args, **kwargs):
    """Return future object which calls callback function on request to return 'None' which generate ValueError."""
    return MockFuture(callback=kwargs.get("callback"), data="None")

def exit_function(*args, **kwargs):
    """Mock function for __exit__."""
    pass

def mocked_result(*args, **kwargs):
    """Raise TimeoutError when calling 'result' with (timoeut=5)."""
    if kwargs.get("timeout"):
        raise main.futures.TimeoutError()

def get_mocked_SubscriberClient():
    """Return mock function for 'pubsub_v1.SubscriberClient'."""
    mock_SubscriberClient = mock.Mock()
    mock_SubscriberClient.subscription_path.return_value = "my-subscription-path"
    mock_SubscriberClient.__exit__ = exit_function
    mock_SubscriberClient.__enter__ = mock_SubscriberClient
    return mock_SubscriberClient

def get_mocked_req():
    mocked_req = mock.Mock()
    mocked_req.get_json.return_value = {"PROJECT_ID": "test_pid", "SUBSCRIPTION_ID": "test_sid", "CHRONICLE_DATA_TYPE": "SENSOR_DATA"}
    return mocked_req

@mock.patch("PUBSUB.main.pubsub_v1.SubscriberClient")
class TestGoolePubSubMain(unittest.TestCase):
    """Test cases to verify the 'main' function for the script"""

    @mock.patch("PUBSUB.main.build_payload")
    def test_callback(self, mocked_build_payload, mocked_SubscriberClient):
        """Test case to verify we call the 'build_payload' when receiving the data from publisher."""
        mock_SubscriberClient = get_mocked_SubscriberClient()
        mock_SubscriberClient.subscribe.side_effect = mocked_subscribe
        mocked_SubscriberClient.return_value = mock_SubscriberClient

        main.main(req=get_mocked_req())

        self.assertEqual(mocked_build_payload.call_count, 1)
        mocked_build_payload.assert_called_with({"id": 1, "type": "Sensor data"})

    @mock.patch("builtins.print")
    @mock.patch("PUBSUB.main.build_payload")
    def test_callback_value_error(self, mocked_build_payload, mocked_print, mocked_SubscriberClient):
        """Test case to verify we raise an error with expected message on encountering ValueError from JSON loads."""

        mock_SubscriberClient = get_mocked_SubscriberClient()
        mock_SubscriberClient.subscribe.side_effect = mocked_subscribe_value_error
        mocked_SubscriberClient.return_value = mock_SubscriberClient

        with self.assertRaises(ValueError):
            main.main(req=get_mocked_req())

        actual_calls = mocked_print.mock_calls[-2:] # Get last 2 call on 'print' method
        expected_calls = [
            mock.call(
                "ERROR: Unexpected data format received while collecting \
                    message details from subscription"
            ),
            mock.call("Message: None")
        ]
        self.assertEqual(actual_calls, expected_calls)

    @mock.patch("PUBSUB.main.build_payload")
    def test_future_TimeoutError(self, mocked_build_payload, mocked_SubscriberClient):
        """Test case to verify we call 'cancel' and 'result' functions when we encounter 'TimeoutError'."""
        mock_future = mock.Mock()
        mock_future.cancel.return_value = None
        mock_future.result.side_effect = mocked_result
        mock_SubscriberClient = get_mocked_SubscriberClient()
        mock_SubscriberClient.subscribe.return_value = mock_future
        mocked_SubscriberClient.return_value = mock_SubscriberClient

        main.main(req=get_mocked_req())

        self.assertEqual(mock_future.result.call_count, 2)
        self.assertEqual(mock_future.cancel.call_count, 1)

    @mock.patch("PUBSUB.main.ingest")
    def test_ingest_remaining_payload_in_the_end(self, mocked_ingest, mocked_SubscriberClient):
        """Test case to verify we ingest remaining PAYLOAD in the end."""
        mock_SubscriberClient = get_mocked_SubscriberClient()
        mock_SubscriberClient.subscribe.side_effect = mocked_subscribe
        mocked_SubscriberClient.return_value = mock_SubscriberClient

        main.main(req=get_mocked_req())

        self.assertEqual(mocked_ingest.call_count, 1)
        mocked_ingest.assert_called_with([json.dumps({"id": 1, "type": "Sensor data"})], "SENSOR_DATA")
